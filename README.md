# ELASPIC REST API

[![docs](https://img.shields.io/badge/docs-v0.1.1-blue.svg)](https://elaspic.gitlab.io/elaspic-rest-api/v0.1.1/)
[![pipeline status](https://gitlab.com/elaspic/elaspic-rest-api/badges/v0.1.1/pipeline.svg)](https://gitlab.com/elaspic/elaspic-rest-api/commits/v0.1.1/)
[![coverage report](https://gitlab.com/elaspic/elaspic-rest-api/badges/v0.1.1/coverage.svg)](https://elaspic.gitlab.io/elaspic-rest-api/v0.1.1/htmlcov/)

## Development

```bash
uvicorn elaspic_rest_api.app:app --host 0.0.0.0 --port 8000 --reload \
    --log-level=debug --log-config .gitlab/docker/logconfig.ini --env-file .env
```

## Deployment

```bash
docker run --tty --env-file .env --env HOST_USER_ID=9284 \
    --env=GUNICORN_CMD_ARGS="--bind 0.0.0.0:8080 --workers 1" \
    --volume /home/kimlab1/database_data/elaspic:/home/kimlab1/database_data/elaspic:rw \
    affb2a451524
```

## Creating Docker image

```bash
# For a private repo, you may need to set the CONDA_BLD_REQUEST_HEADER environment variable
export CONDA_BLD_REQUEST_HEADER="PRIVATE-TOKEN: <your_access_token>"

# Replate "870684925" with the ID of the build for which you want to create the image
export CONDA_BLD_ARCHIVE_URL="https://gitlab.com/api/v4/projects/22388857/jobs/870684925/artifacts"

docker build --build-arg CONDA_BLD_ARCHIVE_URL .gitlab/docker/
```
