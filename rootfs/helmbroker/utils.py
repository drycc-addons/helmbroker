import os
import yaml
import json
import subprocess

from .config import INSTANCES_PATH, ADDONS_PATH
from .loader import read_addons_file


def command(cmd, *args, output_type="text"):
    status, output = subprocess.getstatusoutput("%s %s" % (cmd, " ".join(args)))
    if output_type == "yaml":
        return yaml.load(output, Loader=yaml.Loader)
    elif output_type == "json":
        return json.loads(output)
    return status, output


get_instance_path = lambda instance_id: os.path.join(INSTANCES_PATH, instance_id)
get_chart_path = lambda instance_id: os.path.join(get_instance_path(instance_id), "chart")
get_plan_path = lambda instance_id: os.path.join(get_instance_path(instance_id), "plan")


def get_addon_path(service_id, plan_id):
    services = read_addons_file()
    service = [addon for addon in [addons for _, addons in services.items()]
               if addon['id'] == service_id][0]
    plan = [plan for plan in service['plans'] if plan['id'] == plan_id][0]
    service_name = f'{service["name"]}-{service["version"]}'
    plan_name = plan['name']
    service_path = f'{ADDONS_PATH}/{service_name}'
    plan_path = f'{service_path}/plans/{plan_name}'
    return service_path, plan_path


def get_addon_name(service_id):
    services = read_addons_file()
    service = [addon for addon in [addons for _, addons in services.items()]
               if addon['id'] == service_id][0]
    return service['name']


def get_or_create_instance_meta(instance_id):
    pass


def get_or_create_binding_meta(binding_id, credential):
    pass