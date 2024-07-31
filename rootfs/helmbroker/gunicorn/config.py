import os
from os.path import dirname, realpath

import faulthandler
faulthandler.enable()

bind = '0.0.0.0'
workers = int(os.environ.get('GUNICORN_WORKERS', 4))

pythonpath = dirname(dirname(dirname(realpath(__file__))))
timeout = 1200
pidfile = '/tmp/gunicorn.pid'
logger_class = 'helmbroker.gunicorn.logging.Logging'
loglevel = 'info'
errorlog = '-'
accesslog = '-'
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s "%(a)s"'


def worker_int(worker):
    """Print a stack trace when a worker receives a SIGINT or SIGQUIT signal."""
    worker.log.warning('worker terminated')
    import traceback
    traceback.print_stack()


def worker_abort(worker):
    """Print a stack trace when a worker receives a SIGABRT signal, generally on timeout."""
    worker.log.warning('worker aborted')
    import traceback
    traceback.print_stack()
