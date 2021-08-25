import os
import time
import yaml

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
            "description": "%s in progress at %s" % (instance_id, time.time())
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
        data["last_operation"]["description"] = output
    else:
        data["last_operation"]["state"] = OperationState.SUCCEEDED
        data["last_operation"]["description"] = "succeeded at %s" % time.time()


def bind(instance_id: str,
         binding_id: str,
         details: BindDetails,
         async_allowed: bool,
         **kwargs) -> Binding:
    data = {
        "binding_id": binding_id,
        "credential": {
        },
        "last_operation": {
            "state": OperationState.IN_PROGRESS,
            "description": "%s in progress at %s" % (binding_id, time.time())
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
        data["last_operation"]["description"] = templates

    credential_template = yaml.load(templates.split('bind.yaml')[1], Loader=yaml.Loader)
    success_flag = True
    for _ in credential_template['credential']:
        status, val = get_cred_value(details.context["namespace"], _['ValueFrom'])
        if status != 0:
            success_flag = False
        data[_['name']] = val
    if success_flag:
        data['last_operation'] = {
            'state': OperationState.SUCCEEDED,
            'description': OperationState.SUCCESSFUL_BOUND,
        }
    else:
        data['last_operation'] = {
            'state': OperationState.FAILED,
            'description': OperationState.FAILED,
        }
    dump_binding_meta(instance_id, data)


def deprovision(instance_id: str, details: DeprovisionDetails):
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