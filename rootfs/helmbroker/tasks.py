import os
import time
import yaml
import shutil

from .config import INSTANCES_PATH
from .utils import command, get_plan_path, get_chart_path, get_cred_value
from .meta import dump_instance_meta, dump_binding_meta, load_instance_meta
from openbrokerapi.service_broker import *


def provision(instance_id: str, details: ProvisionDetails):
    data = {
        "id": instance_id,
        "details": {
            "service_id": details.service_id,
            "plan_id" : details.plan_id,
            "context" : details.context,
            "parameters": details.parameters,
        },
        "last_operation": {
            "state": OperationState.IN_PROGRESS,
            "description": "provision %s in progress at %s" % (instance_id, time.time())
        }
    }
    dump_instance_meta(instance_id, data)
    chart_path = get_chart_path(instance_id)
    values_file =  os.path.join(get_plan_path(instance_id), "values.yaml")
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
        data["last_operation"]["state"] = OperationState.FAILED
        data["last_operation"]["description"] = "provision error:\n%s" % output
    else:
        data["last_operation"]["state"] = OperationState.SUCCEEDED
        data["last_operation"]["description"] = "provision succeeded at %s" % time.time()


def update(instance_id: str, details: UpdateDetails):
    data = {
        "id": instance_id,
        "details": {
            "service_id": details.service_id,
            "plan_id" : details.plan_id,
            "context" : details.context,
            "parameters": details.parameters,
        },
        "last_operation": {
            "state": OperationState.IN_PROGRESS,
            "description": "update %s in progress at %s" % (instance_id, time.time())
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
        data["last_operation"]["state"] = OperationState.FAILED
        data["last_operation"]["description"] = "update %s failed: %s" % (instance_id, output)
    else:
        data["last_operation"]["state"] = OperationState.SUCCEEDED
        data["last_operation"]["description"] = "update %s succeeded at %s" % (instance_id, time.time())


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
            "state": OperationState.IN_PROGRESS,
            "description": "binding %s in progress at %s" % (binding_id, time.time())
        }
    }
    dump_binding_meta(instance_id, data)

    chart_path = get_chart_path(instance_id)
    values_file =  os.path.join(get_plan_path(instance_id), "values.yaml")
    args = [
        "template",
        details.context["instance_name"],
        chart_path,
        "-f",
        values_file
    ]
    status, templates = command("helm", *args)  # output: templates.yaml
    if status != 0:
        data["last_operation"]["state"] = OperationState.FAILED
        data["last_operation"]["description"] = "binding %s failed: %s" % (instance_id, templates)

    credential_template = yaml.load(templates.split('bind.yaml')[1], Loader=yaml.Loader)
    success_flag = True
    errors = []
    for _ in credential_template['credential']:
        status, val = get_cred_value(details.context["namespace"], _['ValueFrom'])
        if status != 0:
            success_flag = False
            errors.append(val)
        data[_['name']] = val
    if success_flag:
        data['last_operation'] = {
            'state': OperationState.SUCCEEDED,
            'description': "binding %s succeeded at %s" % (instance_id, time.time())
        }
    else:
        data['last_operation'] = {
            'state': OperationState.FAILED,
            'description': "binding %s failed: %s" % (instance_id, ','.join(errors))
        }
    dump_binding_meta(instance_id, data)


def deprovision(instance_id: str):
    data = load_instance_meta(instance_id)
    data["last_operation"]["state"] = OperationState.IN_PROGRESS
    data["last_operation"]["description"] = "deprovision %s in progress at %s" % (instance_id, time.time())
    dump_instance_meta(instance_id)
    command(
        "helm",
        "uninstall",
        data["details"]["context"]["instance_name"],
        "--namespace",
        data["details"]["context"]["namespace"],
    )
    status, output = command("kubectl", "delete", "ns", data["details"]["context"]["namespace"])
    if status != 0:
        data["last_operation"]["state"] = OperationState.FAILED
        data["last_operation"]["description"] = "deprovision error:\n%s" % output
    else:
        data["last_operation"]["state"] = OperationState.SUCCEEDED
        data["last_operation"]["description"] = "deprovision succeeded at %s" % time.time()
        shutil.rmtree(os.path.join(INSTANCES_PATH, instance_id), ignore_errors=True)