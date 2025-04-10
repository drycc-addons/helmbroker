ARG CODENAME
FROM registry.drycc.cc/drycc/base:${CODENAME}

ENV DRYCC_UID=1001 \
  DRYCC_GID=1001 \
  DRYCC_HOME_DIR=/workspace \
  PYTHON_VERSION="3.12" \
  HELM_VERSION="3.17.2" \
  KUBECTL_VERSION="1.32.3"

RUN groupadd drycc --gid ${DRYCC_GID} \
  && useradd drycc -u ${DRYCC_UID} -g ${DRYCC_GID} -s /bin/bash -m -d ${DRYCC_HOME_DIR}

COPY . ${DRYCC_HOME_DIR}
WORKDIR ${DRYCC_HOME_DIR}

RUN buildDeps='musl-dev' \
  && install-packages ${buildDeps} patch openssl ca-certificates \
  && install-stack python ${PYTHON_VERSION} \
  && install-stack helm ${HELM_VERSION} \
  && install-stack kubectl ${KUBECTL_VERSION} && . init-stack \
  && python3 -m venv ${DRYCC_HOME_DIR}/.venv \
  && source ${DRYCC_HOME_DIR}/.venv/bin/activate \
  && pip3 install --disable-pip-version-check --no-cache-dir -r ${DRYCC_HOME_DIR}/requirements.txt \
  && chown -R ${DRYCC_UID}:${DRYCC_GID} ${DRYCC_HOME_DIR} \
  # set env
  && echo "source ${DRYCC_HOME_DIR}/.venv/bin/activate" >> /opt/drycc/python/profile.d/python.sh \
  # cleanup
  && scanelp ${DRYCC_HOME_DIR}/.venv/lib > runtime.txt \
  && apt-get purge -y --auto-remove ${buildDeps} \
  && install-packages $(< runtime.txt) \
  && apt-get autoremove -y \
  && apt-get clean -y \
  && rm -rf \
        /usr/share/doc \
        /usr/share/man \
        /usr/share/info \
        /usr/share/locale \
        /var/lib/apt/lists/* \
        /var/log/* \
        /var/cache/debconf/* \
        /etc/systemd \
        /lib/lsb \
        /lib/udev \
        /usr/lib/`echo $(uname -m)`-linux-gnu/gconv/IBM* \
        /usr/lib/`echo $(uname -m)`-linux-gnu/gconv/EBC* \
  && mkdir -p /usr/share/man/man{1..8}

USER ${DRYCC_UID}
WORKDIR ${DRYCC_HOME_DIR}
CMD ["bin/boot"]
EXPOSE 8000
