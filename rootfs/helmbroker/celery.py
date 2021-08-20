import os
from celery import Celery


app = Celery(
    'helmbroker',
    broker=os.environ["HELMBROKER_CELERY_BROKER"],
    backend=os.environ["HELMBROKER_CELERY_BACKEND"],
    include=['helmbroker.tasks']
)
app.conf.update(result_expires=3600)


if __name__ == '__main__':
    app.start()
