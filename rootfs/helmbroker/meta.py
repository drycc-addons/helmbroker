import os
import json
import time
from jsonschema import validate
from .utils import get_instance_path, get_instance_file
from .config import ADDONS_PATH

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
                "description": {"type": "string"}
            }
        },
        "last_modified_time": {"type": "number"}
    },
}


def load_instance_meta(instance_id):
    file = get_instance_file(instance_id)
    with open(file) as f:
        data = json.load(f)
        validate(instance=data, schema=INSTANCE_META_SCHEMA)
        return data


def dump_instance_meta(instance_id, data):
    data["last_modified_time "] = time.time()
    file = get_instance_file(instance_id)
    validate(instance=data, schema=INSTANCE_META_SCHEMA)
    with open(file, "w") as f:
        f.write(json.dumps(data, sort_keys=True, indent=2))


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


def load_binding_meta(instance_id):
    file = os.path.join(get_instance_path(instance_id), "binding.json")
    with open(file, 'r') as f:
        data = json.loads(f.read())
        validate(instance=data, schema=INSTANCE_META_SCHEMA)
        return data


def dump_binding_meta(instance_id, data):
    data["last_modified_time "] = time.time()
    file = os.path.join(get_instance_path(instance_id), "binding.json")
    validate(instance=data, schema=INSTANCE_META_SCHEMA)
    with open(file, "w") as f:
        f.write(json.dumps(data, sort_keys=True, indent=2))


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
