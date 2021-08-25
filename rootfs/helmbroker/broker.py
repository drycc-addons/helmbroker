import os
import shutil

from openbrokerapi.errors import ErrInstanceAlreadyExists, ErrAsyncRequired, \
    ErrBindingAlreadyExists, ErrBadRequest, ErrInstanceDoesNotExist
from openbrokerapi.service_broker import *

from .meta import load_instance_meta, load_binding_meta, dump_binding_meta
from .utils import get_instance_path, get_chart_path, get_plan_path, \
    get_addon_path, get_addon_name, get_addon_updateable
from .tasks import provision, bind, deprovision, update
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
        instance_meta = dump_binding_meta(instance_id)
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
        instance_path = get_instance_path(instance_id)
        bind_yaml = f'{instance_path}/bind.yaml'
        shutil.rmtree(bind_yaml)
        return UnbindSpec(is_async=False)

    def update(self,
               instance_id: str,
               details: UpdateDetails,
               async_allowed: bool,
               **kwargs
               ) -> UpdateServiceSpec:
        instance_path = get_instance_path(instance_id)
        if not os.path.exists(instance_path):
            raise ErrBadRequest("Instance %s does not exist" % instance_id)
        is_plan_updateable = get_addon_updateable(instance_id)
        if not is_plan_updateable:
            raise ErrBadRequest("Instance %s does not updateable" % instance_id)
        if not async_allowed:
            raise ErrAsyncRequired()
        plan_path = get_plan_path(instance_id)
        # delete the pre plan
        shutil.rmtree(plan_path)
        _, addon_plan_path = get_addon_path(details.service_id, details.plan_id)
        # add the new plan
        shutil.copy(addon_plan_path, plan_path)
        update.delay(instance_id, details)
        return UpdateServiceSpec(is_async=True)

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

        deprovision.delay(instance_id)
        return DeprovisionServiceSpec(is_async=True)

    def last_operation(self,
                       instance_id: str,
                       operation_data: Optional[str],
                       **kwargs
                       ) -> LastOperation:
        data = load_instance_meta(instance_id)
        return LastOperation(
            data["last_operation"]["state"],
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
            data["last_operation"]["state"],
            data["last_operation"]["description"]
        )
