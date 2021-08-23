import os
import yaml
import json
import subprocess

from .config import INSTANCES_PATH


def command(cmd, *args, output_type="text"):
    status, output = subprocess.getstatusoutput("%s %s" % (cmd, " ".join(args)))
    if output_type == "yaml":
        return yaml.load(output, Loader=yaml.Loader)
    elif output_type == "json":
        return json.loads(output)
    return status, output


get_instance_path = lambda instance_id: os.path.join(INSTANCES_PATH, instance_id)
get_chart_path = lambda instance_id: os.path.join(get_instance_path(instance_id), "chart")
get_plan_path = lambda instance_id: os.path.join(get_instance_path(instance_id), "plan")

def get_addon_path(service_id, plan_id):
    return ""


def get_or_create_instance_meta(instance_id):
    pass