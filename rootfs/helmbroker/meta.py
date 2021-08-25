import os
import json
from jsonschema import validate
from .config import INSTANCES_PATH, ADDONS_PATH

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
                "parameters": {"type": "object"},
            }
        },
        "last_operation": {
            "type": "object",
            "properties": {
                "state": {"type": "string"},
                "description": {"type": "string"}
            }
        }
    },
}


def load_instance_meta(instance_id):
    file = os.path.join(INSTANCES_PATH, instance_id, "instance.json")
    with open(file) as f:
        data = json.load(f)
        validate(instance=data, schema=INSTANCE_META_SCHEMA)
        return data


def dump_instance_meta(instance_id, data):
    file = os.path.join(INSTANCES_PATH, instance_id, "instance.json")
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
        }
    }
}


def load_binding_meta(instance_id):
    file = os.path.join(INSTANCES_PATH, instance_id, "binding.json")
    with open(file, 'r') as f:
        data = json.loads(f.read())
        validate(instance=data, schema=INSTANCE_META_SCHEMA)
        return data


def dump_binding_meta(instance_id, data):
    file = os.path.join(INSTANCES_PATH, instance_id, "binding.json")
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
        print("save addons.json")
        f.write(json.dumps(data, sort_keys=True, indent=2))
