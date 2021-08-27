import os
import yaml
import json
import subprocess

from .config import INSTANCES_PATH, ADDONS_PATH
from .meta import load_addons_meta


def command(cmd, *args, output_type="text"):
    status, output = subprocess.getstatusoutput("%s %s" % (cmd, " ".join(args))) # noqa
    if output_type == "yaml":
        return yaml.load(output, Loader=yaml.Loader)
    elif output_type == "json":
        return json.loads(output)
    return status, output


get_instance_path = lambda instance_id: os.path.join(INSTANCES_PATH, instance_id) # noqa
get_chart_path = lambda instance_id: os.path.join(get_instance_path(instance_id), "chart") # noqa
get_plan_path = lambda instance_id: os.path.join(get_instance_path(instance_id), "plan") # noqa


def get_addon_path(service_id, plan_id):
    services = load_addons_meta()
    service = [addon for addon in [addons for _, addons in services.items()]
               if addon['id'] == service_id][0]
    plan = [plan for plan in service['plans'] if plan['id'] == plan_id][0]
    service_name = f'{service["name"]}-{service["version"]}'
    plan_name = plan['name']
    service_path = f'{ADDONS_PATH}/{service_name}/chart/{service["name"]}'
    plan_path = f'{ADDONS_PATH}/{service_name}/plans/{plan_name}'
    return service_path, plan_path


def get_addon_meta(service_id):
    services = load_addons_meta()
    service = [addon for addon in [addons for _, addons in services.items()]
               if addon['id'] == service_id][0]
    return service


def get_addon_name(service_id):
    service = get_addon_meta(service_id)
    return service['name']


def get_addon_updateable(service_id):
    service = get_addon_meta(service_id)
    return service.get('plan_updateable', False)


def get_addon_bindable(service_id):
    service = get_addon_meta(service_id)
    return service.get('bindable', False)


def get_cred_value(ns, source):
    if source.get('serviceRef'):
        return get_service_key_value(ns, source['serviceRef'])
    if source.get('configMapRef'):
        return get_config_map_key_value(ns, source['configMapRef'])
    if source.get('secretKeyRef'):
        return get_secret_key_value(ns, source['secretKeyRef'])
    return -1, 'invalid ValueFrom'


def get_service_key_value(ns, service_ref):
    args = [
        "get", "svc", service_ref['name'], "-n", ns, '-o', f'jsonpath="{service_ref["jsonpath"]}"', # noqa
    ]
    return command("kubectl", *args)


def get_config_map_key_value(ns, config_map_ref):
    args = [
        "get", "cm", config_map_ref['name'], "-n", ns, '-o', f'jsonpath="{config_map_ref["jsonpath"]}"', # noqa
    ]
    return command("kubectl", *args)


def get_secret_key_value(ns, secret_ref):
    args = [
        "get", "secret", secret_ref['name'], "-n", ns, '-o', f'jsonpath="{secret_ref["jsonpath"]}"', # noqa
    ]
    return command("kubectl", *args)
