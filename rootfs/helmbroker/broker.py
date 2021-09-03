import os
import time
import shutil
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
    get_instance_file, load_instance_meta, load_binding_meta, \
    dump_instance_meta, load_addons_meta
from .tasks import provision, bind, deprovision, update


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
        os.makedirs(instance_path, exist_ok=True)
        chart_path, plan_path = (
            get_chart_path(instance_id), get_plan_path(instance_id))
        addon_chart_path, addon_plan_path = (
            get_addon_path(details.service_id, details.plan_id))
        shutil.copytree(addon_chart_path, chart_path)
        shutil.copytree(addon_plan_path, plan_path)
        data = {
            "id": instance_id,
            "details": {
                "service_id": details.service_id,
                "plan_id": details.plan_id,
                "context": details.context,
                "parameters": details.parameters,
            },
            "last_operation": {
                "state": OperationState.IN_PROGRESS.value,
                "description": (
                    "provision %s in progress at %s" % (
                        instance_id, time.time()))
            }
        }
        with InstanceLock(instance_id):
            dump_instance_meta(instance_id, data)
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
        instance_path = get_instance_path(instance_id)
        if os.path.exists(instance_path):
            if not os.path.exists(get_instance_file(instance_id)):
                return DeprovisionServiceSpec(
                    is_async=False, operation=OperationState.SUCCEEDED)
        else:
            raise ErrInstanceDoesNotExist()
        if not async_allowed:
            raise ErrAsyncRequired()
        deprovision.delay(instance_id)
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
