import yaml
import json
import subprocess


def command(cmd, *args, output_type="text"):
    output = subprocess.getoutput("%s %s" % (cmd, " ".join(args)))
    if output_type == "yaml":
        return yaml.load(output, Loader=yaml.Loader)
    elif output_type == "json":
        return json.loads(output)
    return output