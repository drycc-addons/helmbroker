import os
import shutil
from .utils import command, get_plan_path, get_chart_path, \
    get_or_create_instance_meta, get_or_create_binding_meta
from openbrokerapi.service_broker import *


def provision(instance_id: str,
              details: ProvisionDetails,
              async_allowed: bool,
              **kwargs) -> ProvisionedServiceSpec:
    chart_path = get_chart_path(instance_id)
    values_file =  os.path.join(get_plan_path(instance_id), "values.yaml")
    args = [
        "install",
        details.context["instance_name"],
        chart_path,
        "--namespace",
        details.context["namespace"],
        "--create-namespace",
        "--output",
        "--wait",
        "--timeout 30m0s"
        "-f",
        values_file
    ]
    status, output = command("helm", *args)
    if status != 0:
        return ProvisionedServiceSpec(state="status error: %s" % status, operation=output)
    else:
        config = get_or_create_instance_meta(instance_id)
        return ProvisionedServiceSpec(
            dashboard_url=config.get("dashboard_url", None),
            state=ProvisionState.SUCCESSFUL_CREATED,
            operation=config.get("operation", None),
        )


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
