# For more information, please refer to https://aka.ms/vscode-docker-python
FROM ubuntu:20.04

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install system requirements
RUN apt-get -qq -o=Dpkg::Use-Pty=0 update \
  && apt-get -y -qq -o=Dpkg::Use-Pty=0 install \
  python \
  sendmail \
  && rm -rf /var/lib/apt/lists/*

# Install pip requirements
ADD requirements.txt .
RUN python -m pip install -r requirements.txt

WORKDIR /app
ADD . /app

# Switching to a non-root user, please refer to https://aka.ms/vscode-docker-python-user-rights
RUN useradd appuser && chown -R appuser /app
USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["gunicorn", "src.elaspic_rest_api.app:app", "--bind", "0.0.0.0:8000", "--worker-class", "aiohttp.GunicornWebWorker", "--reload", "--access-logfile", "-"]
