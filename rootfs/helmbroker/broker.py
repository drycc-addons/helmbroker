import os
import shutil
import logging
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

from .utils import get_instance_path, get_chart_path, get_plan_path, \
    get_addon_path, get_addon_updateable, get_addon_bindable, InstanceLock, \
    load_instance_meta, load_binding_meta, load_addons_meta, \
    get_addon_allow_paras, verify_parameters, get_addon_archive
from .tasks import provision, bind, deprovision, update

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
        allow_paras = get_addon_allow_paras(details.service_id)
        not_allow_keys, required_keys = verify_parameters(
            allow_paras, details.parameters)
        if not_allow_keys:
            raise ErrBadRequest(
                msg="parameters %s does not allowed" % not_allow_keys)
        if required_keys:
            raise ErrBadRequest(
                msg="required parameters %s not exists" % required_keys)
        os.makedirs(instance_path, exist_ok=True)
        chart_path, plan_path = (
            get_chart_path(instance_id), get_plan_path(instance_id))
        addon_chart_path, addon_plan_path = (
            get_addon_path(details.service_id, details.plan_id))
        shutil.copytree(addon_chart_path, chart_path)
        shutil.copytree(addon_plan_path, plan_path)
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
        chart_path, plan_path = (
            get_chart_path(instance_id), get_plan_path(instance_id))
        shutil.copy(f'{plan_path}/bind.yaml', f'{chart_path}/templates')
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
        instance_path = get_instance_path(instance_id)
        binding_info = f'{instance_path}/binding.json'
        if os.path.exists(binding_info):
            os.remove(binding_info)
        return UnbindSpec(is_async=False)

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
        allow_paras = get_addon_allow_paras(details.service_id)
        logger.debug(
            f"service instance update parameters: {details.parameters}")
        not_allow_keys, required_keys = verify_parameters(
            allow_paras, details.parameters)
        if not_allow_keys:
            raise ErrBadRequest(
                msg="parameters %s does not allowed" % not_allow_keys)
        if required_keys:
            raise ErrBadRequest(
                msg="required parameters %s not exists" % required_keys)
        if not async_allowed:
            raise ErrAsyncRequired()
        if details.plan_id is not None:
            plan_path = get_plan_path(instance_id)
            # delete the pre plan
            shutil.rmtree(plan_path, ignore_errors=True)
            _, addon_plan_path = get_addon_path(
                details.service_id, details.plan_id)
            # add the new plan
            shutil.copytree(addon_plan_path, plan_path)
        update.delay(instance_id, details)
        return UpdateServiceSpec(is_async=True)

    def deprovision(self,
                    instance_id: str,
                    details: DeprovisionDetails,
                    async_allowed: bool,
                    **kwargs) -> DeprovisionServiceSpec:
        if not os.path.exists(get_instance_path(instance_id)):
            raise ErrInstanceDoesNotExist()
        with InstanceLock(instance_id):
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
        data = load_instance_meta(instance_id)
        return LastOperation(
            OperationState(data["last_operation"]["state"]),
            data["last_operation"]["description"]
        )

    def last_binding_operation(self,
                               instance_id: str,
                               binding_id: str,
                               operation_data: Optional[str],
                               **kwargs
                               ) -> LastOperation:
        data = load_binding_meta(instance_id)
        return LastOperation(
            OperationState(data["last_operation"]["state"]),
            data["last_operation"]["description"]
        )
