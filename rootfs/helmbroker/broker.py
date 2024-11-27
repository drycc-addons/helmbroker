import os
import logging
import time
from typing import Union, List, Optional

from openbrokerapi.catalog import ServicePlan
from openbrokerapi.errors import ErrInstanceAlreadyExists, ErrAsyncRequired, \
    ErrBindingAlreadyExists, ErrBadRequest, ErrInstanceDoesNotExist, \
    ServiceException
from openbrokerapi.service_broker import ServiceBroker, Service, \
    ProvisionDetails, ProvisionedServiceSpec, ProvisionState, GetBindingSpec, \
    BindDetails, Binding, BindState, UnbindDetails, UnbindSpec, \
    UpdateDetails, UpdateServiceSpec, DeprovisionDetails, \
    DeprovisionServiceSpec, LastOperation, OperationState

from .utils import verify_parameters, new_instance_lock
from .database.fetch import fetch_chart_plan
from .database.query import get_instance_path, get_chart_path, get_plan_path, \
    get_addon_updateable, get_addon_bindable, get_addon_allow_params, \
    get_addon_archive, get_binding_file, get_instance_file
from .database.metadata import load_instance_meta, load_binding_meta, load_addons_meta, \
    save_instance_meta
from .tasks import provision, bind, deprovision, update, unbind

logger = logging.getLogger(__name__)


class HelmServiceBroker(ServiceBroker):

    def catalog(self) -> Union[Service, List[Service]]:
        services = load_addons_meta()
        service_objs = []
        for _, addons in services.items():
            plans_objs = []
            for plan in addons['plans']:
                plans_objs.append(ServicePlan(**plan))
            addons['plans'] = plans_objs
            service_objs.append(Service(**addons))
        return service_objs

    def provision(self,
                  instance_id: str,
                  details: ProvisionDetails,
                  async_allowed: bool,
                  **kwargs) -> ProvisionedServiceSpec:
        instance_path = get_instance_path(instance_id)
        if os.path.exists(instance_path):
            raise ErrInstanceAlreadyExists()
        if not async_allowed:
            raise ErrAsyncRequired()
        if get_addon_archive(details.service_id):
            raise ErrBadRequest(
                msg="This addon has archived.")
        allow_params = get_addon_allow_params(details.service_id)
        not_allow_keys, required_keys = verify_parameters(
            allow_params, details.parameters)
        if not_allow_keys:
            raise ErrBadRequest(
                msg="parameters %s does not allowed" % not_allow_keys)
        if required_keys:
            raise ErrBadRequest(
                msg="required parameters %s not exists" % required_keys)
        os.makedirs(instance_path, exist_ok=True)
        chart_path, plan_path = get_chart_path(instance_id), get_plan_path(instance_id)
        fetch_chart_plan(details.service_id, chart_path, details.plan_id, plan_path)
        provision.delay(instance_id, details)
        return ProvisionedServiceSpec(state=ProvisionState.IS_ASYNC)

    def get_binding(self,
                    instance_id: str,
                    binding_id: str,
                    **kwargs
                    ) -> GetBindingSpec:
        data = load_binding_meta(instance_id)
        return GetBindingSpec(
            data["credentials"],
        )

    def bind(self,
             instance_id: str,
             binding_id: str,
             details: BindDetails,
             async_allowed: bool,
             **kwargs
             ) -> Binding:
        is_addon_bindable = get_addon_bindable(details.service_id)
        if not is_addon_bindable:
            raise ErrBadRequest(
                msg="Instance %s does not bindable" % instance_id)
        instance_meta = load_instance_meta(instance_id)
        if not (instance_meta and
                instance_meta['last_operation']['state'] == 'succeeded'):
            raise ErrBadRequest(
                msg="This instance %s is not ready" % instance_id)
        instance_path = get_instance_path(instance_id)
        if os.path.exists(f'{instance_path}/bind.json'):
            raise ErrBindingAlreadyExists()
        bind(instance_id, binding_id, details, async_allowed, **kwargs)
        data = load_binding_meta(instance_id)
        if data["last_operation"]["state"] == OperationState.SUCCEEDED.value:
            return Binding(state=BindState.SUCCESSFUL_BOUND,
                           credentials=data["credentials"])
        else:
            raise ServiceException(data["last_operation"]["description"])

    def unbind(self,
               instance_id: str,
               binding_id: str,
               details: UnbindDetails,
               async_allowed: bool,
               **kwargs
               ) -> UnbindSpec:
        logger.debug(f"unbind instance {instance_id}")
        unbind.delay(instance_id)
        return UnbindSpec(is_async=True)

    def update(self,
               instance_id: str,
               details: UpdateDetails,
               async_allowed: bool,
               **kwargs
               ) -> UpdateServiceSpec:
        instance_path = get_instance_path(instance_id)
        if not os.path.exists(instance_path):
            raise ErrBadRequest(msg="Instance %s does not exist" % instance_id)
        is_plan_updateable = get_addon_updateable(details.service_id)
        if not is_plan_updateable:
            raise ErrBadRequest(
                msg="Instance %s does not updateable" % instance_id)
        allow_params = get_addon_allow_params(details.service_id)
        logger.debug(
            f"service instance update parameters: {details.parameters}")
        not_allow_keys, required_keys = verify_parameters(
            allow_params, details.parameters)
        if not_allow_keys:
            raise ErrBadRequest(
                msg="parameters %s does not allowed" % not_allow_keys)
        if required_keys:
            raise ErrBadRequest(
                msg="required parameters %s not exists" % required_keys)
        if not async_allowed:
            raise ErrAsyncRequired()
        if details.plan_id is not None:
            chart_path, plan_path = get_chart_path(instance_id), get_plan_path(instance_id)
            fetch_chart_plan(details.service_id, chart_path, details.plan_id, plan_path)
        data = load_instance_meta(instance_id)
        data['last_operation']["state"] = OperationState.IN_PROGRESS.value
        data['last_operation']["description"] = (
            f"update {instance_id} in progress at {time.time()}")
        save_instance_meta(instance_id, data)
        update.delay(instance_id, details)
        return UpdateServiceSpec(is_async=True)

    def deprovision(self,
                    instance_id: str,
                    details: DeprovisionDetails,
                    async_allowed: bool,
                    **kwargs) -> DeprovisionServiceSpec:
        if not os.path.exists(get_instance_path(instance_id)):
            raise ErrInstanceDoesNotExist()
        with new_instance_lock(instance_id):
            data = load_instance_meta(instance_id)
            operation = data["last_operation"]["operation"]
            if operation == "provision":
                if not async_allowed:
                    raise ErrAsyncRequired()
                deprovision.delay(instance_id)
            elif operation == "deprovision":
                return DeprovisionServiceSpec(
                    is_async=True, operation=operation)
        return DeprovisionServiceSpec(is_async=True)

    def last_operation(self,
                       instance_id: str,
                       operation_data: Optional[str],
                       **kwargs
                       ) -> LastOperation:
        if os.path.exists(get_instance_file(instance_id)):
            data = load_instance_meta(instance_id)
            return LastOperation(
                OperationState(data["last_operation"]["state"]),
                data["last_operation"]["description"]
            )
        return LastOperation(OperationState.IN_PROGRESS)

    def last_binding_operation(self,
                               instance_id: str,
                               binding_id: str,
                               operation_data: Optional[str],
                               **kwargs
                               ) -> LastOperation:
        if os.path.exists(get_binding_file(instance_id)):
            data = load_binding_meta(instance_id)
            return LastOperation(
                OperationState(data["last_operation"]["state"]),
                data["last_operation"]["description"]
            )
        return LastOperation(OperationState.IN_PROGRESS)
