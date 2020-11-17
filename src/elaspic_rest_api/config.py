import os
import os.path as op

DATA_DIR = os.environ["DATA_DIR"]
SECRET_KEY = os.environ["SECRET_KEY"]
SLURM_MASTER_USER = os.environ["SLURM_MASTER_USER"]
SLURM_MASTER_HOST = os.environ["SLURM_MASTER_HOST"]
SENTRY_DSN = os.getenv("SENTRY_DSN")
SITE_IP = os.getenv("SITE_IP", "0.0.0.0")
SITE_PORT = os.getenv("SITE_PORT", 8080)

NOREPLY_EMAIL = "no-reply@kimlab.org"
ADMIN_EMAIL = "kimlab.webserver@gmail.com"

SITE_NAME = "ELASPIC"
SITE_URL = "http://{}:{}".format(SITE_IP, SITE_PORT)
PRODUCTION_SITE_URL = "http://elaspic.kimlab.org"

ELASPIC_VERSION = "0.1.42"

DB_NAME_ELASPIC = os.environ["DB_NAME_ELASPIC"]
DB_NAME_WEBSERVER = os.environ["DB_NAME_WEBSERVER"]
DB_HOST = os.environ["DB_HOST"]
DB_PORT = int(os.environ["DB_PORT"])
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_CONNECTION_PARAMS = dict(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD)

SCRIPTS_DIR = op.join(DATA_DIR, "scripts")

# Jobsubmitter
PROVEAN_LOCK_DIR = op.join(DATA_DIR, "locks", "sequence")
MODEL_LOCK_DIR = op.join(DATA_DIR, "locks", "model")
MUTATION_LOCK_DIR = op.join(DATA_DIR, "locks", "mutation")

# Email configuration
EMAIL_USE_TLS = bool(os.getenv("EMAIL_USE_TLS"))
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "0"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
