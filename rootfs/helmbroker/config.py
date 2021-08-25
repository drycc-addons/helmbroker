import os

HELMBROKER_ROOT = os.environ.get("HELMBROKER_CELERY_BROKER", '/etc/helmbroker')

ADDONS_PATH = os.path.join(HELMBROKER_ROOT, 'addons')
CONFIG_PATH = os.path.join(HELMBROKER_ROOT, 'config')
INSTANCES_PATH = os.path.join(HELMBROKER_ROOT, 'instances')


class Config:
    DEBUG = os.environ.get("DEBUG", False)
    if not os.path.exists(ADDONS_PATH):
        os.makedirs(ADDONS_PATH)
