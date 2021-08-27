import os
import time
import yaml
import shutil

from openbrokerapi.service_broker import ProvisionDetails, OperationState, \
    UpdateDetails, BindDetails

from .celery import app
from .config import INSTANCES_PATH
from .utils import command, get_plan_path, get_chart_path, get_cred_value
from .meta import dump_instance_meta, dump_binding_meta, load_instance_meta


@app.task(serializer='pickle')
def provision(instance_id: str, details: ProvisionDetails):
    data = {
        "id": instance_id,
        "details": {
            "service_id": details.service_id,
            "plan_id": details.plan_id,
            "context": details.context,
            "parameters": details.parameters,
        },
        "last_operation": {
            "state": OperationState.IN_PROGRESS.value,
            "description": "provision %s in progress at %s" % (instance_id, time.time())  # noqa
        }
    }
    dump_instance_meta(instance_id, data)
    chart_path = get_chart_path(instance_id)
    values_file = os.path.join(get_plan_path(instance_id), "values.yaml")
    args = [
        "install",
        details.context["instance_name"],
        chart_path,
        "--namespace",
        details.context["namespace"],
        "--create-namespace",
        "--wait",
        "--timeout 30m0s"
        "-f",
        values_file
    ]

    status, output = command("helm", *args)
    if status != 0:
        data["last_operation"]["state"] = OperationState.FAILED.value
        data["last_operation"]["description"] = "provision error:\n%s" % output
    else:
        data["last_operation"]["state"] = OperationState.SUCCEEDED.value
        data["last_operation"]["description"] = "provision succeeded at %s" % time.time()  # noqa
    dump_instance_meta(instance_id, data)


@app.task(serializer='pickle')
def update(instance_id: str, details: UpdateDetails):
    data = {
        "id": instance_id,
        "details": {
            "service_id": details.service_id,
            "plan_id": details.plan_id,
            "context": details.context,
            "parameters": details.parameters,
        },
        "last_operation": {
            "state": OperationState.IN_PROGRESS.value,
            "description": "update %s in progress at %s" % (instance_id, time.time())  # noqa
        }
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
        "--timeout 30m0s"
        "-f",
        values_file
    ]

    status, output = command("helm", *args)
    if status != 0:
        data["last_operation"]["state"] = OperationState.FAILED.value
        data["last_operation"]["description"] = "update %s failed: %s" % (instance_id, output)  # noqa
    else:
        data["last_operation"]["state"] = OperationState.SUCCEEDED.value
        data["last_operation"]["description"] = "update %s succeeded at %s" % (instance_id, time.time())  # noqa
    dump_instance_meta(instance_id, data)


@app.task(serializer='pickle')
def bind(instance_id: str,
         binding_id: str,
         details: BindDetails,
         async_allowed: bool,
         **kwargs):
    data = {
        "binding_id": binding_id,
        "credential": {
        },
        "last_operation": {
            "state": OperationState.IN_PROGRESS.value,
            "description": "binding %s in progress at %s" % (binding_id, time.time())  # noqa
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
        values_file
    ]
    status, templates = command("helm", *args)  # output: templates.yaml
    if status != 0:
        data["last_operation"]["state"] = OperationState.FAILED.value
        data["last_operation"]["description"] = "binding %s failed: %s" % (instance_id, templates)  # noqa

    credential_template = yaml.load(templates.split('bind.yaml')[1], Loader=yaml.Loader)  # noqa
    success_flag = True
    errors = []
    for _ in credential_template['credential']:
        status, val = get_cred_value(details.context["namespace"], _['ValueFrom'])  # noqa
        if status != 0:
            success_flag = False
            errors.append(val)
        data[_['name']] = val
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


@app.task()
def deprovision(instance_id: str):
    data = load_instance_meta(instance_id)
    data["last_operation"]["state"] = OperationState.IN_PROGRESS.value
    data["last_operation"]["description"] = "deprovision %s in progress at %s" % (instance_id, time.time())  # noqa
    dump_instance_meta(instance_id, data)
    command(
        "helm",
        "uninstall",
        data["details"]["context"]["instance_name"],
        "--namespace",
        data["details"]["context"]["namespace"],
    )
    status, output = command("kubectl", "delete", "ns", data["details"]["context"]["namespace"])  # noqa
    if status != 0:
        data["last_operation"]["state"] = OperationState.FAILED.value
        data["last_operation"]["description"] = "deprovision error:\n%s" % output  # noqa
    else:
        data["last_operation"]["state"] = OperationState.SUCCEEDED.value
        data["last_operation"]["description"] = "deprovision succeeded at %s" % time.time()  # noqa
        shutil.rmtree(os.path.join(INSTANCES_PATH, instance_id), ignore_errors=True)  # noqa
    dump_instance_meta(instance_id, data)
