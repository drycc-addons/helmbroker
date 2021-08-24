import os
import yaml
from .config import INSTANCES_PATH

INSTANCE_META_FILE = os.path.join(INSTANCES_PATH, "instance.yaml")

class InstanceMeta(object):
    """
    {
        "id": "instance_id",
        "details": {
            "service_id": "service_id",
            "plan_id" : "plan_id",
            "context" : {

            },
            "parameters": {

            }
        },
        "last_operation": {
            "state": "Ready",
            "description": "everything is ok."
        }
    }
    """
    def __init__(self, id, details, last_operation):
        self.id = id
        self.details = details
        self.last_operation = last_operation
    
    @classmethod
    def load(cls, file=INSTANCE_META_FILE):
        with open(file) as f:
            data = yaml.load(f, Loader=yaml.Loader)
            return cls(data["id"], data["details"], data["last_operation"])

    def dump(self, file=INSTANCE_META_FILE):
        with open(file, "w") as f:
            yaml.dump(
                {
                    "id": self.id,
                    "details": self.details,
                    "last_operation": self.last_operation
                },
                Loader=yaml.Loader
            )