import os
import shutil
import time
import yaml

from openbrokerapi.service_broker import ProvisionDetails, OperationState, \
    UpdateDetails, BindDetails

from .celery import app
from .utils import command, get_plan_path, get_chart_path, get_cred_value, \
    InstanceLock, get_instance_file, dump_instance_meta, dump_binding_meta, \
    load_instance_meta


@app.task(serializer='pickle')
def provision(instance_id: str, details: ProvisionDetails):
    with InstanceLock(instance_id):
        chart_path = get_chart_path(instance_id)
        bind_yaml = f'{chart_path}/templates/bind.yaml'
        if os.path.exists(bind_yaml):
            os.remove(bind_yaml)
        if os.path.exists(f'{chart_path}/requirements.lock'):
            args = [
                "dependency",
                "update",
                "--skip-refresh",
                chart_path,
            ]
            command("helm", *args)
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
            "10m0s",
            "-f",
            values_file,
            "--set",
            f"fullnameOverride=helmbroker-{details.context['instance_name']}"
        ]

        status, output = command("helm", *args)
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
        data['details']['service_id'] = details.parameters
    data['last_operation'] = {
        "state": OperationState.IN_PROGRESS.value,
        "description": "update %s in progress at %s" % (instance_id, time.time())  # noqa
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
        "10m0s",
        "-f",
        values_file,
        "--set",
        f"fullnameOverride=helmbroker-{details.context['instance_name']}"
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
        "credentials": {},
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
        values_file,
        "--set",
        f"fullnameOverride=helmbroker-{details.context['instance_name']}"
    ]
    status, templates = command("helm", *args)  # output: templates.yaml
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
        data = load_instance_meta(instance_id)
        data["last_operation"]["state"] = OperationState.IN_PROGRESS.value
        data["last_operation"]["description"] = "deprovision %s in progress at %s" % (instance_id, time.time())  # noqa
        dump_instance_meta(instance_id, data)
        status, output = command(
            "helm",
            "uninstall",
            data["details"]["context"]["instance_name"],
            "--namespace",
            data["details"]["context"]["namespace"],
        )
        if status != 0:
            data["last_operation"]["state"] = OperationState.FAILED.value
            data["last_operation"]["description"] = (
                "deprovision error:\n%s" % output)
            shutil.copy(get_instance_file(instance_id), "%s.%s" % (
                get_instance_file(instance_id),
                time.time()
            ))
        else:
            data["last_operation"]["state"] = OperationState.SUCCEEDED.value
            data["last_operation"]["description"] = (
                "deprovision succeeded at %s" % time.time())
        os.remove(get_instance_file(instance_id))
        dump_instance_meta(instance_id, data)
