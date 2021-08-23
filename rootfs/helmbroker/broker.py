import os
import shutil
from typing import Union, List
from openbrokerapi import api
from openbrokerapi.api import ServiceBroker
from openbrokerapi.catalog import ServicePlan
from openbrokerapi.service_broker import *

from .utils import get_instance_path, get_chart_path, get_plan_path, get_addon_path
from .tasks import provision

class HelmServiceBroker(ServiceBroker):

    def catalog(self) -> Union[Service, List[Service]]:
        return [Service(
            id='server',
            name='server',
            description='service description',
            bindable=True,
            plans=[
                ServicePlan(
                    id='server-1:1-1',
                    name='1-1',
                    description='plan description',
                ),
                ServicePlan(
                    id='server-2:2-2',
                    name='2-2',
                    description='plan description',
                )
            ],
            plan_updateable=True,
        )]

    def provision(self,
                  instance_id: str,
                  details: ProvisionDetails,
                  async_allowed: bool,
                  **kwargs) -> ProvisionedServiceSpec:
        instance_path = get_instance_path(instance_id)
        if os.path.exists(instance_path):
            return ProvisionedServiceSpec(
                state=ProvisionState.IDENTICAL_ALREADY_EXISTS
            )
        os.makedirs(instance_path, exist_ok=True)
        chart_path, plan_path =get_chart_path(instance_id), get_plan_path(instance_id)
        addon_chart_path, addon_plan_path = get_addon_path(details.service_id, details.plan_id)
        shutil.copy(addon_chart_path, chart_path)
        shutil.copy(addon_plan_path, plan_path)
        if async_allowed:
            provision.delay(instance_id, details. async_allowed, **kwargs)
            return ProvisionedServiceSpec(state=ProvisionState.IS_ASYNC)
        return provision(instance_id, details. async_allowed, **kwargs)

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
        return Binding(credentials={"url": "postgres://1.1.1.1", "passwd": "123"})

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
        # Delete service instance
        # ...

        return DeprovisionServiceSpec(is_async=False)
