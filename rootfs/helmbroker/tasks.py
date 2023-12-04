import os
import time
import shutil
import yaml
import base64
import logging

from openbrokerapi.service_broker import ProvisionDetails, OperationState, \
    UpdateDetails, BindDetails

from .celery import app
from .utils import get_plan_path, get_chart_path, get_cred_value, \
    InstanceLock, dump_instance_meta, dump_binding_meta, load_instance_meta, \
    get_instance_file, helm, dump_raw_values

logger = logging.getLogger(__name__)


@app.task(serializer='pickle')
def provision(instance_id: str, details: ProvisionDetails):
    with InstanceLock(instance_id):
        chart_path = get_chart_path(instance_id)
        bind_yaml = f'{chart_path}/templates/bind.yaml'
        if os.path.exists(bind_yaml):
            os.remove(bind_yaml)
        if os.path.exists(f'{chart_path}/Chart.yaml'):
            args = [
                "dependency",
                "update",
                chart_path,
            ]
            helm(instance_id, *args)
        values_file = os.path.join(get_plan_path(instance_id), "values.yaml")
        args = [
            "install",
            details.context["instance_name"],
            chart_path,
            "--namespace",
            details.context["namespace"],
            "--create-namespace",
            "--wait",
            "--timeout",
            "25m0s",
            "-f",
            values_file,
            "--set",
            f"fullnameOverride=helmbroker-{details.context['instance_name']}"
        ]
        logger.debug(f"helm install parameters :{details.parameters}")
        if details.parameters and "rawValues" in details.parameters \
                and details.parameters.get("rawValues", ""):
            values = str(base64.b64decode(details.parameters["rawValues"]), "utf-8")  # noqa
            raw_values_file = dump_raw_values(instance_id, values)
            args.extend(["-f", raw_values_file])
            details.parameters.pop("rawValues")
        if details.parameters:
            for k, v in details.parameters.items():
                args.extend(["--set", f"{k}={v}"])
        logger.debug(f"helm install args:{args}")
        status, output = helm(instance_id, *args)
        data = load_instance_meta(instance_id)
        if status != 0:
            data["last_operation"]["state"] = OperationState.FAILED.value
            data["last_operation"]["description"] = (
                "provision error:\n%s" % output)
        else:
            data["last_operation"]["state"] = OperationState.SUCCEEDED.value
            data["last_operation"]["description"] = (
                "provision succeeded at %s" % time.time())
        dump_instance_meta(instance_id, data)


@app.task(serializer='pickle')
def update(instance_id: str, details: UpdateDetails):
    data = load_instance_meta(instance_id)
    if details.service_id:
        data['details']['service_id'] = details.service_id
    if details.plan_id:
        data['details']['service_id'] = details.plan_id
    if details.context:
        data['details']['context'] = details.context
    if details.parameters:
        data['details']['parameters'] = details.parameters
    data['last_operation'] = {
        "state": OperationState.IN_PROGRESS.value,
        "description": (
            "update %s in progress at %s" % (instance_id, time.time()))
    }
    dump_instance_meta(instance_id, data)
    chart_path = get_chart_path(instance_id)
    values_file = os.path.join(get_plan_path(instance_id), "values.yaml")
    args = [
        "upgrade",
        details.context["instance_name"],
        chart_path,
        "--namespace",
        details.context["namespace"],
        "--create-namespace",
        "--wait",
        "--timeout",
        "25m0s",
        "--reuse-values",
        "-f",
        values_file,
        "--set",
        f"fullnameOverride=helmbroker-{details.context['instance_name']}"
    ]
    logger.info(f"helm upgrade parameters: {details.parameters}")
    if details.parameters and "rawValues" in details.parameters \
            and details.parameters.get("rawValues", ""):
        values = str(base64.b64decode(details.parameters["rawValues"]), "utf-8")  # noqa
        raw_values_file = dump_raw_values(instance_id, values)
        args.extend(["-f", raw_values_file])
        details.parameters.pop("rawValues")
    if details.parameters:
        for k, v in details.parameters.items():
            args.extend(["--set", f"{k}={v}"])
    logger.info(f"helm upgrade args:{args}")
    status, output = helm(instance_id, *args)
    if status != 0:
        data["last_operation"]["state"] = OperationState.FAILED.value
        data["last_operation"]["description"] = (
            "update %s failed: %s" % (instance_id, output))
    else:
        data["last_operation"]["state"] = OperationState.SUCCEEDED.value
        data["last_operation"]["description"] = (
            "update %s succeeded at %s" % (instance_id, time.time()))
    dump_instance_meta(instance_id, data)


@app.task(serializer='pickle')
def bind(instance_id: str,
         binding_id: str,
         details: BindDetails,
         async_allowed: bool,
         **kwargs):
    data = {
        "binding_id": binding_id,
        "credentials": {},
        "last_operation": {
            "state": OperationState.IN_PROGRESS.value,
            "description": (
                "binding %s in progress at %s" % (binding_id, time.time()))
        }
    }
    dump_binding_meta(instance_id, data)

    chart_path = get_chart_path(instance_id)
    values_file = os.path.join(get_plan_path(instance_id), "values.yaml")
    args = [
        "template",
        details.context["instance_name"],
        chart_path,
        "-f",
        values_file,
        "--set",
        f"fullnameOverride=helmbroker-{details.context['instance_name']}"
    ]
    status, templates = helm(instance_id, *args)  # output: templates.yaml
    if status != 0:
        data["last_operation"]["state"] = OperationState.FAILED.value
        data["last_operation"]["description"] = "binding %s failed: %s" % (instance_id, templates)  # noqa

    credential_template = yaml.load(templates.split('bind.yaml')[1], Loader=yaml.Loader)  # noqa
    success_flag = True
    errors = []
    for _ in credential_template['credential']:
        if _.get('valueFrom'):
            status, val = get_cred_value(details.context["namespace"], _['valueFrom'])  # noqa
        elif _.get('value'):
            status, val = 0,  _['value']
        else:
            status, val = -1, 'invalid value'
        if status != 0:
            success_flag = False
            errors.append(val)
        else:
            data['credentials'][_['name']] = val
    if success_flag:
        data['last_operation'] = {
            'state': OperationState.SUCCEEDED.value,
            'description': "binding %s succeeded at %s" % (instance_id, time.time())  # noqa
        }
    else:
        data['last_operation'] = {
            'state': OperationState.FAILED.value,
            'description': "binding %s failed: %s" % (instance_id, ','.join(errors))  # noqa
        }
    dump_binding_meta(instance_id, data)
    bind_yaml = f'{chart_path}/templates/bind.yaml'
    if os.path.exists(bind_yaml):
        os.remove(bind_yaml)


@app.task()
def deprovision(instance_id: str):
    with InstanceLock(instance_id):
        shutil.copy(get_instance_file(instance_id), "%s.%s" % (
            get_instance_file(instance_id), time.time()
        ))
        data = load_instance_meta(instance_id)
        data["last_operation"]["operation"] = "deprovision"
        data["last_operation"]["state"] = OperationState.IN_PROGRESS.value
        data["last_operation"]["description"] = (
            "deprovision %s in progress at %s" % (instance_id, time.time()))
        dump_instance_meta(instance_id, data)
        status, output = helm(
            instance_id,
            "uninstall",
            data["details"]["context"]["instance_name"],
            "--namespace",
            data["details"]["context"]["namespace"],
        )
        if status != 0:
            data["last_operation"]["state"] = OperationState.FAILED.value
            data["last_operation"]["description"] = (
                "deprovision error:\n%s" % output)
        else:
            data["last_operation"]["state"] = (
                OperationState.SUCCEEDED.value)
            data["last_operation"]["description"] = (
                "deprovision succeeded at %s" % time.time())
        dump_instance_meta(instance_id, data)
