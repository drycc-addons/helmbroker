import os
from celery import Celery

from flask import current_app, Flask

from helmbroker.config import Config

flask_app = Flask(__name__)
flask_app.config.from_object(Config)

app = Celery(
    'helmbroker',
    broker=os.environ.get("HELMBROKER_CELERY_BROKER"),
    backend=os.environ.get("HELMBROKER_CELERY_BACKEND"),
    include=['helmbroker.tasks']
)

with flask_app.app_context():
    app.conf.update(current_app.config)

if __name__ == '__main__':
    app.start()
