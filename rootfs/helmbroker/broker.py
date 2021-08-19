from typing import Union, List

import openbrokerapi
from openbrokerapi import api
from openbrokerapi.api import ServiceBroker
from openbrokerapi.catalog import ServicePlan
from openbrokerapi.service_broker import *


class HelmServiceBroker(ServiceBroker):
    def catalog(self) -> Union[Service, List[Service]]:
        return Service(
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
        )

    def provision(self,
                  instance_id: str,
                  details: ProvisionDetails,
                  async_allowed: bool,
                  **kwargs) -> ProvisionedServiceSpec:
        # Create service instance
        # ...
        return ProvisionedServiceSpec()

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
