import os


CONFIG_ROOT = os.environ.get("HELMBROKER_CONFIG_ROOT", '/etc/helmbroker')
ADDONS_PATH = os.path.join(CONFIG_ROOT, 'addons')
CONFIG_PATH = os.path.join(CONFIG_ROOT, 'config')
INSTANCES_PATH = os.path.join(CONFIG_ROOT, 'instances')


USERNAME = os.environ.get('HELMBROKER_USERNAME')
PASSWORD = os.environ.get('HELMBROKER_PASSWORD')

VALKEY_URL = os.environ.get("HELMBROKER_VALKEY_URL", 'redis://localhost:6379/0')


class Config:
    DEBUG = bool(os.environ.get('HELMBROKER_DEBUG', True))
