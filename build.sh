#########################################################################
# File Name: build.sh
# Author: ma6174
# mail: ma6174@163.com
# Created Time: 2023年05月10日 星期三 13时14分57秒
#########################################################################
#!/bin/bash
export CODENAME=bookworm
export DEV_REGISTRY=registry.drycc.cc
make test
#make podman-build
#podman tag registry.drycc.cc/drycc/helmbroker:canary registry.uucin.com/lijianguo/helmbroker:canary
#podman push registry.uucin.com/lijianguo/helmbroker:canary
