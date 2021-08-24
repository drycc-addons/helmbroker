import os
import shutil
from typing import Union, List
from openbrokerapi import api
from openbrokerapi.api import ServiceBroker
from openbrokerapi.errors import ErrInstanceAlreadyExists, ErrAsyncRequired, \
    ErrBindingAlreadyExists, ErrBadRequest
from openbrokerapi.service_broker import *

from .meta import load_instance_meta
from .utils import get_instance_path, get_chart_path, get_plan_path, \
    get_addon_path, get_addon_name
from .tasks import provision, bind
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
        provision.delay(instance_id, details, async_allowed, **kwargs)
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
        instance_meta = load_instance_meta(instance_id)
        if not (instance_meta and
                instance_meta['last_operation']['state'] == 'Ready'):
            raise ErrBadRequest(msg="This instance %s is not ready" % instance_id)
        if not async_allowed:
            raise ErrAsyncRequired()
        instance_path = get_instance_path(instance_id)
        if os.path.exists(f'{instance_path}/bind.yaml'):
            raise ErrBindingAlreadyExists()
        chart_path, plan_path = get_chart_path(instance_id), get_plan_path(instance_id)
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
        # Delete service instance
        # ...

        return DeprovisionServiceSpec(is_async=False)

    def last_operation(self,
                       instance_id: str,
                       operation_data: Optional[str],
                       **kwargs
                       ) -> LastOperation:
        """
        Further readings `CF Broker API#LastOperation <https://docs.cloudfoundry.org/services/api.html#polling>`_

        :param instance_id: Instance id provided by the platform
        :param operation_data: Operation data received from async operation
        :param kwargs: May contain additional information, improves compatibility with upstream versions
        :rtype: LastOperation
        """
        raise NotImplementedError()

    def last_binding_operation(self,
                               instance_id: str,
                               binding_id: str,
                               operation_data: Optional[str],
                               **kwargs
                               ) -> LastOperation:
        """
        Further readings `CF Broker API#LastOperationForBindings <https://github.com/openservicebrokerapi/servicebroker/blob/v2.14/spec.md#polling-last-operation-for-service-bindings>`_
        Must be implemented if `Provision`, `Update`, or `Deprovision` are async.

        :param instance_id: Instance id provided by the platform
        :param binding_id: Binding id provided by the platform
        :param operation_data: Operation data received from async operation
        :param kwargs: May contain additional information, improves compatibility with upstream versions
        :rtype: LastOperation
        """
        raise NotImplementedError()