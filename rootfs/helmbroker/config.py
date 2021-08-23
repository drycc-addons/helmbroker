import yaml

HELMBROKER_ROOT = '/etc/helmbroker'
ADDONS_PATH = HELMBROKER_ROOT + '/addons'
CONFIG_PATH = HELMBROKER_ROOT + '/config'


class Config:
    with open(CONFIG_PATH, 'r') as f:
        repositorie = yaml.load(f.read())
