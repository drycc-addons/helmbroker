import os
import fcntl
import yaml
import json
import subprocess
import time
import base64
import copy
import logging

from jsonschema import validate
from .config import INSTANCES_PATH, ADDONS_PATH, CONFIG_PATH

logger = logging.getLogger(__name__)

REGISTRY_CONFIG_SUFFIX = '.config/helm/registry.json'
REPOSITORY_CACHE_SUFFIX = '.cache/helm/repository'
REPOSITORY_CONFIG_SUFFIX = '.config/helm/repository'
INSTANCE_META_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "details": {
            "type": "object",
            "properties": {
                "service_id": {"type": "string"},
                "plan_id": {"type": "string"},
                "context": {"type": "object"},
                "parameters": {
                    'oneOf': [{'type': 'object'}, {'type': 'null'}]
                },
            },
            "required": [
                "service_id", "plan_id", "context"
            ]
        },
        "last_operation": {
            "type": "object",
            "properties": {
                "state": {"type": "string"},
                "operation": {"type": "string"},
                "description": {"type": "string"}
            }
        },
        "last_modified_time": {"type": "number"}
    },
}
BINDING_META_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "credentials": {
            "type": "object",
        },
        "last_operation": {
            "type": "object",
            "properties": {
                "state": {"type": "string"},
                "description": {"type": "string"}
            }
        },
        "last_modified_time": {"type": "number"}
    }
}
ADDONS_META_SCHEMA = {
    "type": "object",
    "patternProperties": {
        ".*": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "version": {"type": "string"},
            "bindable": {"type": "boolean"},
            "instances_retrievable": {"type": "boolean"},
            "bindings_retrievable": {"type": "boolean"},
            "allow_context_updates": {"type": "boolean"},
            "description": {"type": "string"},
            "tags": {"type": "string"},
            "requires": {"type": "array"},
            "metadata": {"type": "object"},
            "plan_updateable": {"type": "boolean"},
            "dashboard_client": {"type": "object"},
            "plans": {
                "type": "object",
                "id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "metadata": {"type": "object"},
                "free": {"type": "boolean"},
                "bindable": {"type": "boolean"},
                "binding_rotatable": {"type": "boolean"},
                "plan_updateable": {"type": "boolean"},
                "schemas": {"type": "object"},
                "maximum_polling_duration": {"type": "integer"},
                "maintenance_info": {"type": "object"},
                "required": [
                    "id", "name", "description"
                ]
            },
            "required": [
                "id", "name", "description", "bindable", "version", "plans"
            ]
        }
    }
}


def command(cmd, *args, output_type="text"):
    status, output = subprocess.getstatusoutput("%s %s" % (cmd, " ".join(args))) # noqa
    if output_type == "yaml":
        return yaml.load(output, Loader=yaml.Loader)
    elif output_type == "json":
        return json.loads(output)
    return status, output


get_instance_path = lambda instance_id: os.path.join(INSTANCES_PATH, instance_id) # noqa
get_instance_file = lambda instance_id: os.path.join(get_instance_path(instance_id), "instance.json") # noqa
get_chart_path = lambda instance_id: os.path.join(get_instance_path(instance_id), "chart") # noqa
get_plan_path = lambda instance_id: os.path.join(get_instance_path(instance_id), "plan") # noqa


def helm(instance_id, *args, output_type="text"):
    instance_path = get_instance_path(instance_id)
    new_args = []
    new_args.extend(args)
    new_args.extend([
        "--registry-config",
        os.path.join(instance_path, REGISTRY_CONFIG_SUFFIX),
        "--repository-cache",
        os.path.join(instance_path, REPOSITORY_CACHE_SUFFIX),
        "--repository-config",
        os.path.join(instance_path, REPOSITORY_CONFIG_SUFFIX),
    ])
    return command("helm", *new_args, output_type=output_type)


def load_instance_meta(instance_id):
    file = get_instance_file(instance_id)
    with open(file) as f:
        data = json.loads(f.read())
        validate(instance=data, schema=INSTANCE_META_SCHEMA)
        return data


def dump_instance_meta(instance_id, data):
    data["last_modified_time"] = time.time()
    file = get_instance_file(instance_id)
    validate(instance=data, schema=INSTANCE_META_SCHEMA)
    with open(file, "w") as f:
        f.write(json.dumps(data, sort_keys=True, indent=2))


def dump_raw_values(instance_id, data):
    timestamp = time.time()
    instance_path = get_instance_path(instance_id)
    file = f"{instance_path}/raw-values-{timestamp}.yaml"
    with open(file, "w") as f:
        f.write(data)
    return file


def dump_addon_values(service_id, instance_id):
    timestamp = time.time()
    instance_path = get_instance_path(instance_id)
    file = f"{instance_path}/addon-values-{timestamp}.yaml"
    service = _get_addon_meta(service_id)
    logger.debug(f"dump_addon_values service: {service}")
    if not os.path.exists(f'{CONFIG_PATH}/addon-values'):
        return None
    with open(file, "w") as fw:
        with open(f'{CONFIG_PATH}/addon-values', 'r') as f:
            addons_values = yaml.load(f.read(), Loader=yaml.Loader)
            logger.debug(f"dump_addon_values addons_values: {addons_values}")
            addon_values = addons_values.get(service["name"], {}).\
                get(service["version"], {})
            logger.debug(f"dump_addon_values addon_values: {addon_values}")
            if not addon_values:
                return None
            fw.write(yaml.dump(addon_values))
    return file


def load_binding_meta(instance_id):
    file = os.path.join(get_instance_path(instance_id), "binding.json")
    with open(file, 'r') as f:
        data = json.loads(f.read())
        validate(instance=data, schema=INSTANCE_META_SCHEMA)
        return data


def dump_binding_meta(instance_id, data):
    data["last_modified_time"] = time.time()
    file = os.path.join(get_instance_path(instance_id), "binding.json")
    validate(instance=data, schema=INSTANCE_META_SCHEMA)
    with open(file, "w") as f:
        f.write(json.dumps(data, sort_keys=True, indent=2))


def load_addons_meta():
    file = os.path.join(ADDONS_PATH, "addons.json")
    with open(file, 'r') as f:
        data = json.loads(f.read())
        if not data:
            return {}
        validate(instance=data, schema=INSTANCE_META_SCHEMA)
        return data


def dump_addons_meta(data):
    file = os.path.join(ADDONS_PATH, "addons.json")
    validate(instance=data, schema=INSTANCE_META_SCHEMA)
    with open(file, "w") as f:
        f.write(json.dumps(data, sort_keys=True, indent=2))


def get_addon_path(service_id, plan_id):
    service = _get_addon_meta(service_id)
    plan = [plan for plan in service['plans'] if plan['id'] == plan_id][0]
    plan_name = plan['name']
    service_name_path = f'{service["name"]}-{service["version"]}'
    base_path = f"{ADDONS_PATH}/{service_name_path}"
    service_path = f'{base_path}/chart/{service["name"]}'
    plan_path = f'{base_path}/plans/{plan_name}'
    return service_path, plan_path


def get_addon_updateable(service_id):
    service = _get_addon_meta(service_id)
    return service.get('plan_updateable', False)


def get_addon_bindable(service_id):
    service = _get_addon_meta(service_id)
    return service.get('bindable', False)


def get_addon_allow_paras(service_id):
    service = _get_addon_meta(service_id)
    return service.get('allow_parameters', [])


def get_addon_archive(service_id):
    service = _get_addon_meta(service_id)
    return service.get('archive', False)


def get_cred_value(ns, source):
    if source.get('serviceRef'):
        return _get_service_key_value(ns, source['serviceRef'])
    if source.get('configMapRef'):
        return _get_config_map_key_value(ns, source['configMapRef'])
    if source.get('secretKeyRef'):
        return _get_secret_key_value(ns, source['secretKeyRef'])
    return -1, 'invalid valueFrom'


class InstanceLock(object):

    def __init__(self, instance_id):
        self.instance_id = instance_id

    def __enter__(self):
        self.fileno = open(
            os.path.join(INSTANCES_PATH, self.instance_id, "instance.lock"),
            "w"
        )
        fcntl.flock(self.fileno, fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        fcntl.flock(self.fileno, fcntl.LOCK_UN)

    def __del__(self):
        if hasattr(self, "fileno"):
            fcntl.flock(self.fileno, fcntl.LOCK_UN)


def verify_parameters(allow_parameters, parameters):
    """verify parameters allowed or not"""
    def merge_parameters(parameters):
        raw_para_keys = []
        if "rawValues" in parameters:
            raw_values = yaml.safe_load(
                base64.b64decode(parameters["rawValues"]))
            raw_para_keys = _raw_values_format_keys(raw_values)
            parameters.pop("rawValues")
        return set(list(parameters.keys()) + raw_para_keys)

    if not parameters or not allow_parameters:
        return ""
    parameters = merge_parameters(copy.deepcopy(parameters))
    return (
        ",".join(_verify_allow_parameters(allow_parameters, parameters)),
        ",".join(_verify_required_parameters(allow_parameters, parameters)),
    )


def format_paras_to_helm_args(instance_id, parameters, args):
    """

    """
    params = copy.deepcopy(parameters)
    if params and "rawValues" in params \
            and params.get("rawValues", ""):
        values = str(base64.b64decode(params["rawValues"]), "utf-8")  # noqa
        raw_values_file = dump_raw_values(instance_id, values)
        args.extend(["-f", raw_values_file])
        params.pop("rawValues")
    if params:
        for k, v in params.items():
            args.extend(["--set", f"{k}={v}"])
    return args


def _get_addon_meta(service_id):
    services = load_addons_meta()
    service = [addon for addon in [addons for _, addons in services.items()]
               if addon['id'] == service_id][0]
    return service


def _get_service_key_value(ns, service_ref):
    args = [
        "get", "svc", service_ref['name'], "-n", ns, '-o', f"jsonpath=\'{service_ref['jsonpath']}\'", # noqa
    ]
    return command("kubectl", *args)


def _get_config_map_key_value(ns, config_map_ref):
    args = [
        "get", "cm", config_map_ref['name'], "-n", ns, '-o', f"jsonpath=\'{config_map_ref['jsonpath']}\'", # noqa
    ]
    return command("kubectl", *args)


def _get_secret_key_value(ns, secret_ref):
    args = [
        "get", "secret", secret_ref['name'], "-n", ns, '-o', f"jsonpath=\'{secret_ref['jsonpath']}\'", # noqa
    ]
    status, output = command("kubectl", *args)
    if status == 0:
        output = base64.b64decode(output).decode()
    return status, output


def _raw_values_format_keys(raw_values, prefix=''):
    """
    {'a': {'b': 1, 'c': {'d': 2, 'e': 3}}, 'f': 4}
    ->
    ['a.b', 'a.c.d', 'a.c.e', 'a.f']
    """
    keys = []
    for key, value in raw_values.items():
        new_prefix = prefix + '.' + key if prefix else key
        if isinstance(value, dict):
            keys.extend(_raw_values_format_keys(value, new_prefix))
        else:
            keys.append(new_prefix)
    return keys


def _verify_allow_parameters(allow_parameters, parameters):
    error_parameters = set()
    for parameter in parameters:
        error = True
        for allow_parameter in allow_parameters:
            if parameter.startswith("%s." % allow_parameter["name"]) \
                    or parameter == allow_parameter["name"]:
                error = False
                break
        if error:
            error_parameters.add(parameter)
    return error_parameters


def _verify_required_parameters(allow_parameters, parameters):
    error_parameters = set()
    for allow_parameter in allow_parameters:
        if allow_parameter.get("required", False):
            error = True
            for parameter in parameters:
                if parameter.startswith("%s." % allow_parameter["name"]) \
                        or parameter == allow_parameter["name"]:
                    error = False
                    break
            if error:
                error_parameters.add(allow_parameter["name"])
    return error_parameters
