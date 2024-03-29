import os
import shutil
import tarfile
import requests
import yaml

from .config import ADDONS_PATH, CONFIG_PATH
from .utils import dump_addons_meta


def download_file(url, dest):
    if not os.path.exists(dest):
        os.system(f'mkdir -p {dest}')
    filename = url.split('/')[-1]
    file = requests.get(url)
    with open(f"{dest}/{filename}", 'wb') as f:
        f.write(file.content)
    if filename.endswith(".yaml") or filename.endswith(".yml"):
        return yaml.load(file.content.decode(encoding="utf-8"),
                         Loader=yaml.Loader)


def read_file(filename):
    if not os.path.exists(filename):
        return
    with open(filename, 'r') as f:
        file_content = f.read()
    return file_content


def save_file(content, dest, filename):
    if not os.path.exists(dest):
        os.system(f'mkdir -p {dest}')
    with open(f"{dest}/{filename}", 'w') as f:
        f.write(content)


def extract_tgz(tgz_file, dest):
    if not os.path.exists(tgz_file):
        return
    if not os.path.exists(dest):
        os.system(f'mkdir -p {dest}')

    tarobj = tarfile.open(tgz_file, "r:gz")
    for tarinfo in tarobj:
        tarobj.extract(tarinfo.name, dest)
    tarobj.close()


def addons_meta_file():
    meta_files = []
    # get meta.yaml
    for root, dirnames, filenames in os.walk(ADDONS_PATH):
        for filename in filenames:
            if filename == 'meta.yaml':
                meta_files.append(os.path.join(root, filename))
    meta_files = [meta_file.split(ADDONS_PATH)[1] for meta_file in meta_files]
    addons_meta = []
    plans_meta = []
    for meta_file in meta_files:
        if len(meta_file.split('/')) == 3:
            addons_meta.append(meta_file.split('/')[1:])
        else:
            plans_meta.append(meta_file.split('/')[1:])
    addons_dict = {}
    for addon_meta in addons_meta:
        with open(f'{ADDONS_PATH}/{"/".join(addon_meta)}', 'r') as f:
            meta = yaml.load(f.read(), Loader=yaml.Loader)
            meta['tags'] = meta.get('tags').split(', ') if meta.get('tags') else [] # noqa
            meta['plans'] = []
            addons_dict[meta['displayName']] = meta
        addon_plans_meta = []
        for plan_meta in plans_meta:
            if plan_meta[0] == meta['displayName']:
                addon_plans_meta.append(plan_meta)
            elif f'{"-".join(plan_meta[0].split("-")[0:-1])}' == meta['displayName']: # noqa
                addon_plans_meta.append(plan_meta)
        for addon_plan_meta in addon_plans_meta:
            with open(f'{ADDONS_PATH}/{"/".join(addon_plan_meta)}', 'r') as f:
                addons_mata = yaml.load(f.read(), Loader=yaml.Loader)
                addons_dict[meta['displayName']]['plans'].append(addons_mata) # noqa
    dump_addons_meta(addons_dict)


def load_addons(repository):
    if not repository:
        return
    index_name = repository['url'].split('/')[-1]
    local_index_file = f'{ADDONS_PATH}/{index_name}'
    # download index.yaml
    remote_index = requests.get(repository['url']).content.decode(
        encoding="utf-8")
    # compare index.yaml, is update
    local_index = read_file(local_index_file)
    if local_index and remote_index == local_index:
        return
    # delete old repository catalog
    if os.path.exists(ADDONS_PATH):
        shutil.rmtree(ADDONS_PATH, ignore_errors=True)
    else:
        os.makedirs(ADDONS_PATH, exist_ok=True)
    # new index
    save_file(remote_index, ADDONS_PATH, index_name)
    remote_index = yaml.load(remote_index, Loader=yaml.Loader)
    # save index.yaml addons
    for addon_name, v in remote_index.get('entries', {}).items():
        for _ in v:
            url = "/".join(repository["url"].split("/")[0:-1])
            tgz_name = f'{addon_name}-{_["version"]}'
            addon_tgz_url = f'{url}/{tgz_name}.tgz'
            download_file(addon_tgz_url, ADDONS_PATH)
            extract_tgz(f'{ADDONS_PATH}/{tgz_name}.tgz',
                        f'{ADDONS_PATH}/{tgz_name}')
    addons_meta_file()


if __name__ == '__main__':
    with open(f'{CONFIG_PATH}/repositories', 'r') as f:
        repositories = yaml.load(f.read(), Loader=yaml.Loader)
        load_addons(repositories[0])
