import os
import json
import time
import logging
import jsonschema

from ..utils import get_valkey_client
from ..config import ADDONS_PATH

logger = logging.getLogger(__name__)

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
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "version": {"type": "string"},
                "bindable": {"type": "boolean"},
                "instances_retrievable": {"type": "boolean"},
                "bindings_retrievable": {"type": "boolean"},
                "allow_context_updates": {"type": "boolean"},
                "description": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "requires": {"type": "array"},
                "metadata": {"type": "object"},
                "plan_updateable": {"type": "boolean"},
                "dashboard_client": {"type": "object"},
                "plans": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
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
                        },
                        "required": ["id", "name", "description"]
                    },
                    "minItems": 1,

                },
            },
            "required": ["id", "name", "description", "bindable", "version", "plans"]
        },
    },
    "additionalProperties": False,
}


def save_instance_meta(instance_id, data):
    cache_key = f"helmbroker:instance:{instance_id}"
    from .query import get_instance_file
    data["last_modified_time"] = time.time()
    file = get_instance_file(instance_id)
    jsonschema.validate(instance=data, schema=INSTANCE_META_SCHEMA)

    json_data = json.dumps(data, sort_keys=True, indent=2)
    with open(file, "w") as f:
        f.write(json_data)
    get_valkey_client().set(cache_key, json_data)


def load_instance_meta(instance_id):
    cache_key = f"helmbroker:instance:{instance_id}"
    valkey = get_valkey_client()

    json_data = valkey.get(cache_key)
    if not json_data:
        from .query import get_instance_file
        file = get_instance_file(instance_id)
        with open(file) as f:
            json_data = f.read()
            valkey.set(cache_key, json_data)
    return json.loads(json_data)


def save_binding_meta(instance_id, data):
    from .query import get_binding_file
    cache_key = f"helmbroker:binding:{instance_id}"
    data["last_modified_time"] = time.time()
    file = get_binding_file(instance_id)
    jsonschema.validate(instance=data, schema=BINDING_META_SCHEMA)

    json_data = json.dumps(data, sort_keys=True, indent=2)
    with open(file, "w") as f:
        f.write(json_data)
    get_valkey_client().set(cache_key, json_data)


def load_binding_meta(instance_id):
    from .query import get_binding_file
    cache_key = f"helmbroker:binding:{instance_id}"
    valkey = get_valkey_client()
    json_data = valkey.get(cache_key)
    if not json_data:
        file = get_binding_file(instance_id)
        with open(file, 'r') as f:
            json_data = f.read()
            valkey.set(cache_key, json_data)
    return json.loads(json_data)


def save_addons_meta(data):
    cache_key = "helmbroker:addons"
    os.makedirs(ADDONS_PATH, exist_ok=True)
    file = os.path.join(ADDONS_PATH, "addons.json")
    jsonschema.validate(instance=data, schema=ADDONS_META_SCHEMA)

    json_data = json.dumps(data, sort_keys=True, indent=2)
    with open(file, "w") as f:
        f.write(json_data)
    get_valkey_client().set(cache_key, json_data)


def load_addons_meta():
    cache_key = "helmbroker:addons"
    valkey = get_valkey_client()

    json_data = valkey.get(cache_key)
    if not json_data:
        file = os.path.join(ADDONS_PATH, "addons.json")
        with open(file, 'r') as f:
            json_data = f.read()
            valkey.set(cache_key, json_data)
    return json.loads(json_data)
