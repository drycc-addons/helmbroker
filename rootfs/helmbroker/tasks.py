import os
import time
from .utils import command, get_plan_path, get_chart_path, get_or_create_binding_meta
from .meta import dump_instance_meta
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
            "description": "%s in progress at %s" % (instance_id, time.time())
        }
    }
    dump_instance_meta(data)
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
        data["last_operation"]["description"] = output
    else:
        data["last_operation"]["state"] = OperationState.SUCCEEDED
        data["last_operation"]["description"] = "succeeded at %s" % time.time()


def bind(instance_id: str,
         binding_id: str,
         details: BindDetails,
         async_allowed: bool,
         **kwargs) -> Binding:
    chart_path = get_chart_path(instance_id)
    values_file =  os.path.join(get_plan_path(instance_id), "values.yaml")
    args = [
        "template",
        details.context["instance_name"],
        chart_path,
        "-f",
        values_file
    ]
    status, output = command("helm", *args)  # templates.yaml
    if status != 0:
        return Binding(state="status error: %s" % status, operation=output)
    else:
        config = get_or_create_binding_meta(binding_id, output.split('bind.yaml')[1])
        return Binding(
            credentials=config.get("credential", None),
            state=ProvisionState.SUCCESSFUL_CREATED,
            operation=config.get("operation", None),
        )


def deprovision(instance_id: str, details: DeprovisionDetails):
    pass