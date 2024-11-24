import os
import tarfile
import requests
import yaml
import json
import glob
import shutil
import tempfile
import collections


def fetch_addons(repository):
    if not repository:
        return
    temp = tempfile.TemporaryDirectory()
    try:
        index_name = repository['url'].split('/')[-1]
        # download index.yaml
        remote_index = requests.get(repository['url']).content.decode(encoding="utf-8")
        # new index
        with open(f"{temp.name}/{index_name}", 'w') as f:
            f.write(remote_index)
        remote_index = yaml.load(remote_index, Loader=yaml.Loader)
        # save index.yaml addons
        download_urls = {}
        for addon_name, addon_metas in remote_index.get('entries', {}).items():
            download_urls[addon_name] = {}
            for addon_meta in addon_metas:
                url = "/".join(repository["url"].split("/")[0:-1])
                meta_name = f'{addon_name}-{addon_meta["version"]}'
                addon_tgz_url = f'{url}/{meta_name}.tgz'
                _fetch_addon(addon_tgz_url, f'{temp.name}/{meta_name}')
        return _read_addons_meta(temp.name)
    finally:
        temp.cleanup()


def fetch_chart_plan(addon_id, chart_path, plan_id, plan_path):
    from .query import get_addon_meta
    addon_meta = get_addon_meta(addon_id)
    addon_plan = [plan for plan in addon_meta['plans'] if plan['id'] == plan_id][0]
    temp = tempfile.TemporaryDirectory()
    try:
        _fetch_addon(addon_meta['url'], temp.name)
        shutil.rmtree(chart_path, ignore_errors=True)
        shutil.rmtree(plan_path, ignore_errors=True)
        shutil.copytree(os.path.join(temp.name, "chart", addon_meta["name"]), chart_path)
        shutil.copytree(os.path.join(temp.name, "plans", addon_plan['name']), plan_path)
    finally:
        temp.cleanup()


def _fetch_addon(url, dest):
    with tempfile.TemporaryFile(suffix=".tgz") as tgz_file:
        tgz_file.write(requests.get(url).content)
        tgz_file.flush()
        tgz_file.seek(0)
        os.makedirs(dest, exist_ok=True)
        with tarfile.open(fileobj=tgz_file, mode="r:gz") as tarobj:
            for tarinfo in tarobj:
                tarobj.extract(tarinfo.name, dest, filter='data')
        filename1 = os.path.join(dest, "meta.yaml")
        with open(filename1, "r") as f1:
            meta = yaml.load(stream=f1, Loader=yaml.Loader)
            meta['url'] = url
            meta['version'] = str(meta['version'])
            meta['tags'] = [tag.strip() for tag in meta.get('tags').split(',') if tag.strip()]
            with open(os.path.join(dest, "meta.json"), "w") as f2:
                json.dump(meta, f2)
        os.remove(filename1)


def _read_addons_meta(addons_path):
    addons_meta = collections.OrderedDict()
    for metafile in glob.glob(os.path.join(addons_path, "*", "meta.json")):
        with open(metafile) as f1:
            meta = json.load(f1)
            meta['plans'] = []
            metapath = os.path.join(os.path.dirname(metafile))
            for planfile in glob.glob(os.path.join(metapath, "plans", "*", "meta.yaml")):
                with open(planfile, 'r') as f2:
                    plan = yaml.load(f2.read(), Loader=yaml.Loader)
                    meta["plans"].append(plan)
            addons_meta[meta['displayName']] = meta
    return addons_meta


def main():
    from ..config import CONFIG_PATH
    from .metadata import save_addons_meta
    addons_meta = collections.OrderedDict()
    with open(f'{CONFIG_PATH}/repositories', 'r') as f:
        repositories = yaml.load(f.read(), Loader=yaml.Loader)
        for repository in repositories:
            addons_meta.update(fetch_addons(repository))
    save_addons_meta(addons_meta)


if __name__ == '__main__':
    main()
