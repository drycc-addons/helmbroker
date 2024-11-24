import os
from urllib.parse import urlparse, parse_qs, urlencode
from kombu import Exchange, Queue
from celery import Celery
from .config import VALKEY_URL


class Config(object):
    # Celery Configuration Options
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
    worker_prefetch_multiplier = 1
    result_expires = 24 * 60 * 60
    cache_backend = 'django-cache'
    task_default_queue = 'helmbroker.middle'
    task_default_exchange = 'helmbroker.priority'
    task_default_routing_key = 'helmbroker.priority.middle'
    broker_transport_options = {"queue_order_strategy": "sorted"}
    task_create_missing_queues = True
    task_inherit_parent_priority = True
    broker_connection_retry_on_startup = True
    worker_cancel_long_running_tasks_on_connection_loss = True


app = Celery('helmbroker')
app.config_from_object(Config())
app.conf.update(
    timezone=os.environ.get('TZ', 'UTC'),
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
            routing_key='helmbroker.priority.low',
        ),
        Queue(
            'helmbroker.high', exchange=Exchange('helmbroker.priority', type="direct"),
            routing_key='helmbroker.priority.high',
        ),
        Queue(
            'helmbroker.middle', exchange=Exchange('helmbroker.priority', type="direct"),
            routing_key='helmbroker.priority.middle',
        ),
    ),
)
app.autodiscover_tasks(("helmbroker.tasks",))
url = urlparse(VALKEY_URL)
query = parse_qs(url.query)
broker_transport_options = {"queue_order_strategy": "sorted", "visibility_timeout": 43200}
result_backend_transport_options = {}
if 'master_set' in query:
    master_name = query.pop('master_set')[0]
    password = url.netloc.split("@")[0].split(":")[1]
    kwargs = {'sentinel_kwargs': {'password': password}, 'master_name': master_name}
    broker_transport_options.update(kwargs)
    result_backend_transport_options.update(kwargs)
    VALKEY_URL = f"sentinel://{url.netloc}{url.path}?{urlencode(query)}"
app.conf.update(
    broker_url=VALKEY_URL,
    result_backend=VALKEY_URL,
    broker_transport_options=broker_transport_options,
    result_backend_transport_options=result_backend_transport_options,
)

if __name__ == '__main__':
    app.start()
