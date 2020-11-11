from unittest.mock import MagicMock, patch

import pytest

from elaspic_rest_api import config
from elaspic_rest_api import jobsubmitter as js


@pytest.mark.parametrize("restarting", [False, True])
@patch("smtplib.SMTP.sendmail")
def test_send_admin_email(sendmail: MagicMock, restarting: bool):
    item = js.Item(
        run_type="mutations",
        args={
            "job_id": "test-send-job-failed-email",
            "job_type": "mutations",
            "protein_id": "4dkl",
            "mutations": "G1A",
        },
    )
    return_code = js.email.send_admin_email(
        item, system_command="echo 'hello world'", restarting=restarting
    )
    assert not return_code
    assert sendmail.calledonce()


@pytest.mark.parametrize("send_type", ["started", "complete"])
@patch("smtplib.SMTP.sendmail")
def test_send_job_finished_email(sendmail: MagicMock, send_type):
    job_id = "test-send-job-finished-email"
    job_email = config.ADMIN_EMAIL
    return_code = js.email.send_job_finished_email(job_id, job_email, send_type)
    assert not return_code
    assert sendmail.calledonce()
