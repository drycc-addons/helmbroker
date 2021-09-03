import os

HELMBROKER_ROOT = os.environ.get("HELMBROKER_ROOT", '/etc/helmbroker')

ADDONS_PATH = os.path.join(HELMBROKER_ROOT, 'addons')
CONFIG_PATH = os.path.join(HELMBROKER_ROOT, 'config')
INSTANCES_PATH = os.path.join(HELMBROKER_ROOT, 'instances')

USERNAME = os.environ.get('USERNAME')
PASSWORD = os.environ.get('PASSWORD')


class Config:
    DEBUG = bool(os.environ.get('DRYCC_DEBUG', True))
    # Celery Configuration Options
    timezone = "Asia/Shanghai"
    enable_utc = True
    task_serializer = 'pickle'
    accept_content = frozenset([
       'application/data',
       'application/text',
       'application/json',
       'application/x-python-serialize',
    ])
    task_track_started = True
    task_time_limit = 30 * 60
    worker_max_tasks_per_child = 200
    result_expires = 24 * 60 * 60
