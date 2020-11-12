# For more information, please refer to https://aka.ms/vscode-docker-python
FROM ubuntu:20.04

ARG PACKAGE_NAME=elaspic-rest-api
ARG PACKAGE_VERSION=master

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install system requirements
RUN apt-get -qq -o=Dpkg::Use-Pty=0 update \
    && apt-get -y -qq -o=Dpkg::Use-Pty=0 install \
    curl \
    openssh-client \
    python \
    sendmail \
    wget \
    && rm -rf /var/lib/apt/lists/*

SHELL ["/bin/bash", "-c"]

RUN groupadd -g 32766 lucky

RUN mkdir -p /opt/docker/bin \
    && curl -sS https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o miniconda.sh \
    && openssl dgst -sha256 miniconda.sh | grep 879457af6a0bf5b34b48c12de31d4df0ee2f06a8e68768e5758c3293b2daf688 \
    && bash miniconda.sh -b -p /opt/conda \
    && rm miniconda.sh \
    && source /opt/conda/etc/profile.d/conda.sh \
    && conda activate base \
    && conda install -yq -c conda-forge -c defaults tini su-exec \
    && python -m pip install https://gitlab.com/elaspic/${PACKAGE_NAME}/-/archive/master/${PACKAGE_NAME}-${PACKAGE_VERSION}.zip \
    && conda clean -tipy \
    && chgrp -R lucky /opt/conda \
    && chmod -R g=u /opt/conda

COPY logconfig.ini /opt/conda/share/

COPY entrypoint /opt/docker/bin/entrypoint

# Ensure that all containers start with tini and the user selected process.
# Activate the `conda` environment `base` and the devtoolset compiler.
# Provide a default command (`bash`), which will start if the user doesn't specify one.
ENTRYPOINT [ "/opt/conda/bin/tini", "--", "/opt/docker/bin/entrypoint" ]

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD [ "gunicorn", "elaspic_rest_api.app:app", "--bind", "0.0.0.0:${PORT}", \
    "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--log-config", "/opt/conda/share/logconfig.ini", "--access-logfile", "-" ]
