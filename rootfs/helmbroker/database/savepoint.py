import os
import logging
import yaml
import shutil
import datetime

from ..config import CONFIG_PATH
from .query import get_instance_path, get_backups_path, get_addon_meta, get_addon_values_file, \
    get_custom_addon_values_file

logger = logging.getLogger(__name__)


def save_raw_values(instance_id, data):
    file = get_custom_addon_values_file(instance_id)
    with open(file, "w") as f:
        f.write(data)
    return file


def save_addon_values(service_id, instance_id):
    file = get_addon_values_file(instance_id)
    service = get_addon_meta(service_id)
    logger.debug(f"save_addon_values service: {service}")
    if not os.path.exists(f'{CONFIG_PATH}/addon-values'):
        return None
    with open(file, "w") as fw:
        with open(f'{CONFIG_PATH}/addon-values', 'r') as f:
            addons_values = yaml.load(f.read(), Loader=yaml.Loader)
            logger.debug(f"save_addon_values addons_values: {addons_values}")
            addon_values = addons_values.get(service["name"], {}).\
                get(service["version"], {})
            logger.debug(f"save_addon_values addon_values: {addon_values}")
            if not addon_values:
                return None
            fw.write(yaml.dump(addon_values))
    return file


def backup_instance(instance_id):
    now = datetime.datetime.now(datetime.timezone.utc)
    backup_path = os.path.join(get_backups_path(instance_id), now.isoformat())
    os.makedirs(backup_path, exist_ok=True)

    addon_values_file = get_addon_values_file(instance_id)
    if os.path.exists(addon_values_file):
        shutil.copy(addon_values_file, backup_path)
    custom_addon_values_file = get_custom_addon_values_file(instance_id)
    if os.path.exists(custom_addon_values_file):
        shutil.copy(custom_addon_values_file, backup_path)

    instance_path = get_instance_path(instance_id)
    shutil.copytree(os.path.join(instance_path, "plan"), os.path.join(backup_path, "plan"))
    shutil.copytree(os.path.join(instance_path, "chart"), os.path.join(backup_path, "chart"))
