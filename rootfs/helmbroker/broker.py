import os
import shutil
from typing import Union, List
from openbrokerapi import api
from openbrokerapi.api import ServiceBroker, ErrInstanceAlreadyExists, ErrAsyncRequired, ErrInstanceDoesNotExist
from openbrokerapi.service_broker import *

from .meta import InstanceMeta, load_instance_meta
from .utils import get_instance_path, get_chart_path, get_plan_path, \
    get_addon_path, get_addon_name
from .tasks import provision, bind, deprovision
from helmbroker.loader import read_addons_file


class HelmServiceBroker(ServiceBroker):

    def catalog(self) -> Union[Service, List[Service]]:
        services = read_addons_file()
        return [Service(
            **addons
        ) for _, addons in services.items()]

    def provision(self,
                  instance_id: str,
                  details: ProvisionDetails,
                  async_allowed: bool,
                  **kwargs) -> ProvisionedServiceSpec:
        instance_path = get_instance_path(instance_id)
        if os.path.exists(instance_path):
            raise ErrInstanceAlreadyExists("Instance %s already exists" % instance_id)
        if not async_allowed:
            raise ErrAsyncRequired()
        os.makedirs(instance_path, exist_ok=True)
        chart_path, plan_path =get_chart_path(instance_id), get_plan_path(instance_id)
        addon_chart_path, addon_plan_path = get_addon_path(details.service_id, details.plan_id)
        shutil.copy(addon_chart_path, chart_path)
        shutil.copy(addon_plan_path, plan_path)
        provision.delay(instance_id, details)
        return ProvisionedServiceSpec(state=ProvisionState.IS_ASYNC)
    

    def get_binding(self,
                    instance_id: str,
                    binding_id: str,
                    **kwargs
                    ) -> GetBindingSpec:
        return GetBindingSpec()

    def bind(self,
             instance_id: str,
             binding_id: str,
             details: BindDetails,
             async_allowed: bool,
             **kwargs
             ) -> Binding:

        if not (InstanceMeta.load(instance_id) and
                InstanceMeta.load(instance_id)['last_operation']['state'] == 'Ready'):
            return Binding(state="status error: this instance is not ready")
        if not async_allowed:
            raise ErrAsyncRequired()
        instance_path = get_instance_path(instance_id)
        if os.path.exists(f'{instance_path}/bind.yaml'):
            return Binding(state=BindState.IDENTICAL_ALREADY_EXISTS)
        chart_path, plan_path =get_chart_path(instance_id), get_plan_path(instance_id)
        addon_name = get_addon_name(details.service_id)
        shutil.copy(f'{plan_path}/bind.yaml', f'{chart_path}/{addon_name}/templates')
        bind.delay(instance_id, binding_id, details, async_allowed, **kwargs)
        return Binding(state=BindState.IS_ASYNC)

    def unbind(self,
               instance_id: str,
               binding_id: str,
               details: UnbindDetails,
               async_allowed: bool,
               **kwargs
               ) -> UnbindSpec:
        return UnbindSpec(is_async=False)

    def update(self,
               instance_id: str,
               details: UpdateDetails,
               async_allowed: bool,
               **kwargs
               ) -> UpdateServiceSpec:
        # Update service instnce
        return ProvisionedServiceSpec()

    def deprovision(self,
                    instance_id: str,
                    details: DeprovisionDetails,
                    async_allowed: bool,
                    **kwargs) -> DeprovisionServiceSpec:
        instance_path = get_instance_path(instance_id)
        if not os.path.exists(instance_path):
            raise ErrInstanceDoesNotExist("Instance %s not exists" % instance_id)
        if not async_allowed:
            raise ErrAsyncRequired()

        deprovision.delay(instance_id, details)
        return DeprovisionServiceSpec(state=ProvisionState.IS_ASYNC)


    def last_operation(self,
                       instance_id: str,
                       operation_data: Optional[str],
                       **kwargs
                       ) -> LastOperation:
        data = load_instance_meta()
        return LastOperation(
            data["last_operation"]["state"],
            data["last_operation"]["description"]
        )
