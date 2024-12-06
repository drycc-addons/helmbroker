import os
import logging
from flask import Flask, make_response
from openbrokerapi import api, log_util
from helmbroker.broker import HelmServiceBroker
from helmbroker.config import Config, USERNAME, PASSWORD

application = Flask("helmbroker")


@application.route("/healthz")
def healthz():
    return "OK"


@application.route("/readiness")
def readiness():
    if "KUBECONFIG" in os.environ:
        return "OK"
    elif "KUBERNETES_SERVICE_PORT" in os.environ and \
            ("KUBERNETES_SERVICE_HOST" in os.environ or
             "KUBERNETES_CLUSTER_DOMAIN" in os.environ):
        return "OK"
    return make_response("kubernetes not available", 500)


application.config.from_object(Config)
catalog_api = api.get_blueprint(
    HelmServiceBroker(),
    api.BrokerCredentials(USERNAME, PASSWORD),
    log_util.basic_config(level=logging.DEBUG if Config.DEBUG else logging.INFO))
application.register_blueprint(catalog_api)
