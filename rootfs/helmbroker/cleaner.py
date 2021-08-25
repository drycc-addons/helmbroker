import os
import time
import logging
import shutil

from openbrokerapi.service_broker import OperationState

from .config import INSTANCES_PATH
from .meta import load_instance_meta
from .tasks import deprovision

logger = logging.getLogger(__name__)


def clean_instance():
    for instance_id in os.listdir(INSTANCES_PATH):
        if os.path.exists(os.path.join(INSTANCES_PATH, instance_id, "instance.json")):  # noqa
            data = load_instance_meta(instance_id)
            interval = time.time() - data["last_modified_time"]
            if interval > 3600 * 24 and data["last_operation"]["state"] != OperationState.SUCCEEDED:  # noqa
                deprovision.delay(instance_id)
        else:
            shutil.rmtree(os.path.join(INSTANCES_PATH, instance_id), ignore_errors=True)  # noqa


if __name__ == "__main__":
    clean_instance()
