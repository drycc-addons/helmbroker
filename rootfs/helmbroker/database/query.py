import os
import base64

from ..utils import command
from ..config import INSTANCES_PATH
from .metadata import load_addons_meta


def get_instance_path(instance_id):
    return os.path.join(INSTANCES_PATH, instance_id)


def get_instance_file(instance_id):
    return os.path.join(get_instance_path(instance_id), "instance.json")


def get_chart_path(instance_id):
    return os.path.join(get_instance_path(instance_id), "chart")


def get_plan_path(instance_id):
    return os.path.join(get_instance_path(instance_id), "plan")


def get_hooks_path(instance_id):
    return os.path.join(get_plan_path(instance_id), "hooks")


def get_hooks_result_file(instance_id):
    return os.path.join(get_instance_path(instance_id), "hooks-result.json")


def get_binding_file(instance_id):
    return os.path.join(get_instance_path(instance_id), "binding.json")


def get_backups_path(instance_id):
    return os.path.join(get_instance_path(instance_id), "backups")


def get_addon_values_file(instance_id):
    return os.path.join(get_instance_path(instance_id), "addon-values.yaml")


def get_custom_addon_values_file(instance_id):
    return os.path.join(get_instance_path(instance_id), "custom-addon-values.yaml")


def get_addon_updateable(addon_id):
    addon_meta = get_addon_meta(addon_id)
    return addon_meta.get('plan_updateable', False)


def get_addon_bindable(addon_id):
    addon_meta = get_addon_meta(addon_id)
    return addon_meta.get('bindable', False)


def get_addon_allow_params(addon_id):
    addon_meta = get_addon_meta(addon_id)
    return addon_meta.get('allow_parameters', [])


def get_addon_archive(addon_id):
    addon_meta = get_addon_meta(addon_id)
    return addon_meta.get('archive', False)


def get_cred_value(ns, source):
    if source.get('serviceRef'):
        return _get_service_key_value(ns, source['serviceRef'])
    if source.get('configMapRef'):
        return _get_config_map_key_value(ns, source['configMapRef'])
    if source.get('secretKeyRef'):
        return _get_secret_key_value(ns, source['secretKeyRef'])
    return -1, 'invalid valueFrom'


def get_addon_meta(addon_id):
    addons_meta = load_addons_meta()
    addons_meta = [
        addon for addon in [addons for _, addons in addons_meta.items()]
        if addon['id'] == addon_id
    ]
    return addons_meta[0] if len(addons_meta) > 0 else None


def _get_service_key_value(ns, service_ref):
    args = [
        "get", "svc", service_ref['name'], "-n", ns,
        '-o', f"jsonpath=\'{service_ref['jsonpath']}\'",
    ]
    return command("kubectl", *args)


def _get_config_map_key_value(ns, config_map_ref):
    args = [
        "get", "cm", config_map_ref['name'], "-n", ns,
        '-o', f"jsonpath=\'{config_map_ref['jsonpath']}\'",
    ]
    return command("kubectl", *args)


def _get_secret_key_value(ns, secret_ref):
    args = [
        "get", "secret", secret_ref['name'], "-n", ns, '-o',
        f"jsonpath=\'{secret_ref['jsonpath']}\'",
    ]
    status, output = command("kubectl", *args)
    if status == 0:
        output = base64.b64decode(output).decode()
    return status, output
