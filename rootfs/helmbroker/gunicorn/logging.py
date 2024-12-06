from gunicorn.glogging import Logger
from helmbroker.config import Config


class Logging(Logger):
    def access(self, resp, req, environ, request_time):
        # health check endpoints are only logged in debug mode
        if (
            not Config.DEBUG and
            req.path in ['/readiness', '/healthz']
        ):
            return

        Logger.access(self, resp, req, environ, request_time)
