import os
from celery import Celery


class Config:
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
    broker_connection_retry_on_startup = True
    task_default_queue = 'helmbroker.priority.low'
    worker_cancel_long_running_tasks_on_connection_loss = True


app = Celery(
    'helmbroker',
    broker=os.environ.get("DRYCC_RABBITMQ_URL"),
    include=['helmbroker.tasks']
)

app.config_from_object(Config)

if __name__ == '__main__':
    app.start()
