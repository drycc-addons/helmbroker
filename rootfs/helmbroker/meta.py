import os
import json
from jsonschema import validate
from .config import INSTANCES_PATH

INSTANCE_META_FILE = os.path.join(INSTANCES_PATH, "instance.json")
BINDING_META_FILE = os.path.join(INSTANCES_PATH, "binding.yaml")

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


def load_instance_meta(file=INSTANCE_META_FILE):
    with open(file) as f:
        data = json.load(f)
        validate(instance=data, schema=INSTANCE_META_SCHEMA)
        return data


def dump_instance_meta(data, file=INSTANCE_META_FILE):
    validate(instance=data, schema=INSTANCE_META_SCHEMA)
    with open(file, "w") as f:
        json.dump(f, data)


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


def load_binding_meta(file=BINDING_META_FILE):
    with open(file, 'r') as f:
        data = json.loads(f.read())
        validate(instance=data, schema=INSTANCE_META_SCHEMA)
        return data


def dump_binding_meta(data, file=BINDING_META_FILE):
    validate(instance=data, schema=INSTANCE_META_SCHEMA)
    with open(file, "w") as f:
        f.write(json.dumps(data))
