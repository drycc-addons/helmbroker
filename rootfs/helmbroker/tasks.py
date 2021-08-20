from .celery import app


@app.task
def mul(x, y):
    return x * y
