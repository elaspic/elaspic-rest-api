import logging
import re
import smtplib
from email.message import EmailMessage

import bleach
from jinja2 import Environment, PackageLoader, select_autoescape

from elaspic_rest_api import config
from elaspic_rest_api.jobsubmitter.types import Item

j2_env = Environment(
    loader=PackageLoader("elaspic_rest_api", "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

logger = logging.getLogger(__name__)


def send_admin_email(item: Item, system_command: str, restarting: bool = False) -> bool:
    """
    TODO: Rework this to be asyncronous.
    """
    body = [
        "A job with job id {} did not run successfully!".format(item.job_id),
        "It can be restarted with the following system commad:\n'{}'".format(system_command),
        "The log files can be found here:\n{}\n{}\n".format(item.stdout_path, item.stderr_path),
    ]
    restarting_string = "Restarting..." if restarting else "Failed!"
    msg = EmailMessage()
    msg.set_content("\n".join(body))
    msg["Subject"] = f"ELASPIC job {item.job_id} ({item.unique_id}) failed. {restarting_string}"
    msg["From"] = config.EMAIL_HOST_USER
    msg["To"] = config.ADMIN_EMAIL
    try:
        with smtplib.SMTP(config.EMAIL_HOST, config.EMAIL_PORT) as s:
            if config.EMAIL_USE_TLS:
                s.starttls()
            if config.EMAIL_HOST_USER and config.EMAIL_HOST_PASSWORD:
                s.login(config.EMAIL_HOST_USER, config.EMAIL_HOST_PASSWORD)
            s.send_message(msg)
        return False
    except Exception as e:
        logger.error("The following exception occured while trying to send mail: {}".format(e))
        return True


def send_job_finished_email(job_id: str, job_email: str, send_type: str) -> bool:
    """Send email to user.

    Args:
        job_id
        job_email
        send_type:
    """
    # Validate email address
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(?:[a-zA-Z]{2,4}|museum)$", job_email):
        return True

    # Set Subject and content.
    if send_type == "started":
        subject, status = "started", "has been correctly STARTED"
    elif send_type == "complete":
        subject, status = "results", "is COMPLETE"
    else:
        raise ValueError(f"Incorrect send type: {send_type}.")

    # Prepare template and email object.
    template = j2_env.get_template("email.html")
    html_content = template.render(
        {
            "JID": job_id,
            "SITE_NAME": config.SITE_NAME,
            "SITE_URL": config.SITE_URL,
            "SUPPORT_EMAIL": config.ADMIN_EMAIL,
            "status": status,
        }
    )

    text_content = bleach.clean(html_content)

    msg = EmailMessage()
    msg["Subject"] = "%s %s - Job ID: %s" % (config.SITE_NAME, subject, job_id)
    msg["From"] = config.EMAIL_HOST_USER
    msg["To"] = job_email
    msg.set_content(text_content)
    msg.add_alternative(html_content, subtype="html")

    logger.debug("Sending email...")
    try:
        with smtplib.SMTP(config.EMAIL_HOST, config.EMAIL_PORT) as s:
            if config.EMAIL_USE_TLS:
                s.starttls()
            if config.EMAIL_HOST_USER and config.EMAIL_HOST_PASSWORD:
                s.login(config.EMAIL_HOST_USER, config.EMAIL_HOST_PASSWORD)
            s.send_message(msg)
        logger.debug("Email sent successfully! :)")
        return False
    except Exception as e:
        logger.error("The following exception occured while trying to send mail: {}".format(e))
        return True
