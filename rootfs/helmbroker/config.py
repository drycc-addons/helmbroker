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
    CELERY_TIMEZONE = "Asia/Shanghai"
    CELERY_ENABLE_UTC = True
    CELERY_TASK_SERIALIZER = 'pickle'
    CELERY_ACCEPT_CONTENT = frozenset([
        'application/data',
        'application/text',
        'application/json',
        'application/x-python-serialize',
    ])
    CELERY_TASK_TRACK_STARTED = True
    CELERY_TASK_TIME_LIMIT = 30 * 60
    CELERYD_MAX_TASKS_PER_CHILD = 200
    CELERY_TASK_RESULT_EXPIRES = 24 * 60 * 60
