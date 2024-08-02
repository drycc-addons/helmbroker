import os
import time
import yaml
import logging

from openbrokerapi.service_broker import ProvisionDetails, OperationState, \
    UpdateDetails, BindDetails

from .celery import app
from .utils import helm, format_params_to_helm_args, new_instance_lock, run_instance_hooks

from .database.metadata import save_instance_meta, save_binding_meta, load_instance_meta
from .database.savepoint import save_addon_values, backup_instance
from .database.query import get_plan_path, get_chart_path, get_cred_value, get_binding_file

logger = logging.getLogger(__name__)


@app.task(serializer='pickle')
def provision(instance_id: str, details: ProvisionDetails):
    with new_instance_lock(instance_id), run_instance_hooks(instance_id, "provision"):
        backup_instance(instance_id)
        # create instance.json
        save_instance_meta(instance_id, {
            "id": instance_id,
            "details": {
                "service_id": details.service_id, "plan_id": details.plan_id,
                "context": details.context,
                "parameters": details.parameters if details.parameters else {},
            },
            "last_operation": {
                "state": OperationState.IN_PROGRESS.value, "operation": "provision",
                "description": ("provision %s in progress at %s" % (instance_id, time.time()))
            }
        })

        chart_path = get_chart_path(instance_id)
        bind_yaml = f'{chart_path}/templates/bind.yaml'
        if os.path.exists(bind_yaml):
            os.remove(bind_yaml)
        if os.path.exists(f'{chart_path}/Chart.yaml'):
            args = ["dependency", "update", chart_path]
            helm(instance_id, *args)
        values_file = os.path.join(get_plan_path(instance_id), "values.yaml")
        args = [
            "install", details.context["instance_name"], chart_path,
            "--namespace", details.context["namespace"], "--create-namespace",
            "--wait", "--timeout", "25m0s", "-f", values_file,
            "--set", f"fullnameOverride=helmbroker-{details.context['instance_name']}"
        ]
        addon_values_file = save_addon_values(details.service_id, instance_id)
        if addon_values_file:
            args.insert(9, "-f")
            args.insert(10, addon_values_file)
        logger.debug(f"helm install parameters :{details.parameters}")
        args = format_params_to_helm_args(instance_id, details.parameters, args)
        logger.debug(f"helm install args:{args}")
        status, output = helm(instance_id, *args)
        data = load_instance_meta(instance_id)
        if status != 0:
            data["last_operation"]["state"] = OperationState.FAILED.value
            data["last_operation"]["description"] = "provision error:\n%s" % output
        else:
            data["last_operation"]["state"] = OperationState.SUCCEEDED.value
            data["last_operation"]["description"] = "provision succeeded at %s" % time.time()
        save_instance_meta(instance_id, data)


@app.task(serializer='pickle')
def update(instance_id: str, details: UpdateDetails):
    with new_instance_lock(instance_id), run_instance_hooks(instance_id, "update"):
        backup_instance(instance_id)
        data = load_instance_meta(instance_id)
        if details.service_id:
            data['details']['service_id'] = details.service_id
        if details.plan_id:
            data['details']['service_id'] = details.plan_id
        if details.context:
            data['details']['context'] = details.context
        if details.parameters:
            params = data['details']['parameters']
            params.update(details.parameters)
            # remove the key which value is null
            data['details']['parameters'] = {k: v for k, v in params.items() if v != ""}
        data['last_operation']["state"] = OperationState.IN_PROGRESS.value
        data['last_operation']["description"] = "update %s in progress at %s" % (
            instance_id, time.time())
        save_instance_meta(instance_id, data)
        chart_path = get_chart_path(instance_id)
        values_file = os.path.join(get_plan_path(instance_id), "values.yaml")
        args = [
            "upgrade", details.context["instance_name"], chart_path,
            "--namespace", details.context["namespace"], "--create-namespace",
            "--wait", "--timeout", "25m0s", "--reuse-values", "-f", values_file,
            "--set", f"fullnameOverride=helmbroker-{details.context['instance_name']}"
        ]
        addon_values_file = save_addon_values(details.service_id, instance_id)
        if addon_values_file:
            args.insert(10, "-f")
            args.insert(11, addon_values_file)
        params = data['details']['parameters']
        logger.debug(f"helm upgrade parameters: {params}")
        args = format_params_to_helm_args(instance_id, params, args)
        logger.debug(f"helm upgrade args:{args}")
        status, output = helm(instance_id, *args)
        if status != 0:
            data["last_operation"]["state"] = OperationState.FAILED.value
            data["last_operation"]["description"] = "update %s failed: %s" % (instance_id, output)
        else:
            data["last_operation"]["state"] = OperationState.SUCCEEDED.value
            data["last_operation"]["description"] = (
                "update %s succeeded at %s" % (instance_id, time.time()))
        save_instance_meta(instance_id, data)


@app.task(serializer='pickle')
def bind(instance_id: str,
         binding_id: str,
         details: BindDetails,
         async_allowed: bool,
         **kwargs):
    with new_instance_lock(instance_id), run_instance_hooks(instance_id, "bind"):
        backup_instance(instance_id)
        data = {
            "binding_id": binding_id, "credentials": {},
            "last_operation": {
                "state": OperationState.IN_PROGRESS.value,
                "description": "binding %s in progress at %s" % (binding_id, time.time())
            }
        }
        save_binding_meta(instance_id, data)
        chart_path = get_chart_path(instance_id)
        values_file = os.path.join(get_plan_path(instance_id), "values.yaml")
        args = [
            "template", details.context["instance_name"], chart_path,
            "-f", values_file,
            "--set", f"fullnameOverride=helmbroker-{details.context['instance_name']}",
            "--namespace", details.context["namespace"],
        ]
        instance_data = load_instance_meta(instance_id)
        params = instance_data["details"]["parameters"]
        logger.debug(f"helm template parameters: {params}")
        args = format_params_to_helm_args(instance_id, params, args)
        logger.debug(f"helm template args: {args}")
        status, templates = helm(instance_id, *args)  # output: templates.yaml
        if status != 0:
            data["last_operation"]["state"] = OperationState.FAILED.value
            data["last_operation"]["description"] = "binding %s failed: %s" % (
                instance_id, templates)

        credential_template = yaml.load(templates.split('bind.yaml')[1], Loader=yaml.Loader)
        success_flag = True
        errors = []
        for _ in credential_template['credential']:
            if _.get('valueFrom'):
                status, val = get_cred_value(details.context["namespace"], _['valueFrom'])
            elif _.get('value'):
                status, val = 0,  _['value']
            else:
                status, val = -1, 'invalid value'
            if status != 0:
                success_flag = False
                errors.append(val)
            else:
                data['credentials'][_['name']] = val
        if success_flag:
            data['last_operation'] = {
                'state': OperationState.SUCCEEDED.value,
                'description': "binding %s succeeded at %s" % (instance_id, time.time())
            }
        else:
            data['last_operation'] = {
                'state': OperationState.FAILED.value,
                'description': "binding %s failed: %s" % (instance_id, ','.join(errors))
            }
        bind_yaml = f'{chart_path}/templates/bind.yaml'
        if os.path.exists(bind_yaml):
            os.remove(bind_yaml)
        save_binding_meta(instance_id, data)


@app.task(serializer='pickle')
def unbind(instance_id):
    with new_instance_lock(instance_id), run_instance_hooks(instance_id, "deprovision"):
        backup_instance(instance_id)
        binding_file = get_binding_file(instance_id)
        if os.path.exists(binding_file):
            os.remove(binding_file)


@app.task(serializer='pickle')
def deprovision(instance_id: str):
    with new_instance_lock(instance_id), run_instance_hooks(instance_id, "deprovision"):
        backup_instance(instance_id)
        data = load_instance_meta(instance_id)
        data["last_operation"]["operation"] = "deprovision"
        data["last_operation"]["state"] = OperationState.IN_PROGRESS.value
        data["last_operation"]["description"] = (
            "deprovision %s in progress at %s" % (instance_id, time.time()))
        save_instance_meta(instance_id, data)
        args = [
            "uninstall", data["details"]["context"]["instance_name"],
            "--namespace", data["details"]["context"]["namespace"],
        ]
        logger.debug(f"helm uninstall args: {args}")
        status, output = helm(instance_id, *args)
        if status != 0:
            data["last_operation"]["state"] = OperationState.FAILED.value
            data["last_operation"]["description"] = "deprovision error:\n%s" % output
        else:
            data["last_operation"]["state"] = OperationState.SUCCEEDED.value
            data["last_operation"]["description"] = "deprovision succeeded at %s" % time.time()
        save_instance_meta(instance_id, data)
