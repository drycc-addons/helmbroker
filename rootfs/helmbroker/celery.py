import os
from kombu import Exchange, Queue
from celery import Celery


class Config(object):
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
    broker_url = os.environ.get("DRYCC_RABBITMQ_URL", 'amqp://guest:guest@127.0.0.1:5672/')  # noqa
    broker_connection_retry_on_startup = True
    task_default_queue = 'low'
    task_default_exchange = 'helmbroker.priority'
    task_default_routing_key = 'helmbroker.priority.low'
    broker_connection_retry_on_startup = True
    worker_cancel_long_running_tasks_on_connection_loss = True


app = Celery('helmbroker')
app.config_from_object(Config())
app.conf.update(
    task_routes={
        'helmbroker.tasks': {
            'queue': 'low',
            'exchange': 'helmbroker.priority',
            'routing_key': 'helmbroker.priority.high',
        },
    },
    task_queues=(
        Queue(
            'low',
            exchange=Exchange('helmbroker.priority', type="direct"),
            routing_key='helmbroker.priority.low',
            queue_arguments={'x-max-priority': 16},
        ),
    ),
)
app.autodiscover_tasks()


app.config_from_object(Config())

if __name__ == '__main__':
    app.start()
