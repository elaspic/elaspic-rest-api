import pytest

from elaspic_rest_api import jobsubmitter as js


@pytest.mark.asyncio
async def test_main(data_in):
    # TODO: We should look for unique (protein_id, uniprot_domain_pair_ids) pairs when calculating
    # num_protens, but this is not implemented.
    num_proteins = len(data_in["mutations"])
    num_mutations = sum(len(d["mutations"].split(",")) for d in data_in["mutations"])

    ds = js.DataStructures()
    await js.main(data_in, ds)
    assert ds.pre_qsub_queue.qsize() == num_mutations
    assert ds.qsub_queue.qsize() == num_proteins * 2
    assert ds.validation_queue.empty()
    assert not ds.running_jobs
    assert len(ds.monitored_jobs) == 1
    job_key = js.JobKey(
        data_in["mutations"][0]["webserver_job_id"], data_in["mutations"][0]["webserver_job_email"]
    )
    assert len(ds.monitored_jobs[job_key])
