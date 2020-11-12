# ELASPIC REST API

[![conda](https://img.shields.io/conda/dn/ostrokach-forge/elaspic-rest-api.svg)](https://anaconda.org/ostrokach-forge/elaspic-rest-api/)
[![docs](https://img.shields.io/badge/docs-v0.1.0-blue.svg)](https://elaspic.gitlab.io/elaspic-rest-api/v0.1.0/)
[![pipeline status](https://gitlab.com/elaspic/elaspic-rest-api/badges/v0.1.0/pipeline.svg)](https://gitlab.com/elaspic/elaspic-rest-api/commits/v0.1.0/)
[![coverage report](https://gitlab.com/elaspic/elaspic-rest-api/badges/v0.1.0/coverage.svg)](https://elaspic.gitlab.io/elaspic-rest-api/v0.1.0/htmlcov/)

## Development

```bash
uvicorn elaspic_rest_api.app:app --host 0.0.0.0 --port 8000 --reload \
    --log-level=debug --log-config .gitlab/docker/logconfig.ini --env-file .env
```
