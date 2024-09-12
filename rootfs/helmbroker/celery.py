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
    broker_url = os.environ.get("HELMBROKER_RABBITMQ_URL", 'amqp://guest:guest@127.0.0.1:5672/')
    broker_connection_retry_on_startup = True
    task_default_queue = 'helmbroker.low'
    task_default_exchange = 'helmbroker.priority'
    task_default_routing_key = 'helmbroker.priority.low'
    broker_connection_retry_on_startup = True
    worker_cancel_long_running_tasks_on_connection_loss = True


app = Celery('helmbroker')
app.config_from_object(Config())
app.conf.update(
    task_routes={
        'helmbroker.tasks.provision': {
            'queue': 'helmbroker.high',
            'exchange': 'helmbroker.priority', 'routing_key': 'helmbroker.priority.high',
        },
        'helmbroker.tasks.update': {
            'queue': 'helmbroker.high',
            'exchange': 'helmbroker.priority', 'routing_key': 'helmbroker.priority.high',
        },
        'helmbroker.tasks.bind': {
            'queue': 'helmbroker.high',
            'exchange': 'helmbroker.priority', 'routing_key': 'helmbroker.priority.high',
        },
        'helmbroker.tasks.deprovision': {
            'queue': 'helmbroker.middle',
            'exchange': 'helmbroker.priority', 'routing_key': 'helmbroker.priority.middle',
        },
    },
    task_queues=(
        Queue(
            'helmbroker.low', exchange=Exchange('helmbroker.priority', type="direct"),
            routing_key='helmbroker.priority.low', queue_arguments={'x-queue-type': 'quorum'},
        ),
        Queue(
            'helmbroker.high', exchange=Exchange('helmbroker.priority', type="direct"),
            routing_key='helmbroker.priority.high', queue_arguments={'x-queue-type': 'quorum'},
        ),
        Queue(
            'helmbroker.middle', exchange=Exchange('helmbroker.priority', type="direct"),
            routing_key='helmbroker.priority.middle', queue_arguments={'x-queue-type': 'quorum'},
        ),
    ),
)
app.autodiscover_tasks(("helmbroker.tasks",))


app.config_from_object(Config())

if __name__ == '__main__':
    app.start()
