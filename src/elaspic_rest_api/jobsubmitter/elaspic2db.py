import logging
from typing import List, Tuple

from elaspic_rest_api import jobsubmitter as js
from elaspic_rest_api.jobsubmitter.elaspic2types import COI, MutationInfo

logger = logging.getLogger(__name__)

# Local core
get_core_mutation_local_sql = """\
select domain_id as domain_or_interface_id,
    model_filename_wt,
    chain_modeller,
    mutation_modeller
from elaspic_webserver.elaspic_core_mutation_local
where protein_id = %(protein_id)s and mutation = %(mutation)s;
"""

update_core_mutation_local_sql = """\
update elaspic_webserver.elaspic_core_mutation_local mut
set mut.protbert_score = %(protbert_score)s,
    mut.proteinsolver_score = %(proteinsolver_score)s,
    mut.el2_score = %(el2_score)s,
    mut.el2_version = %(el2_version)s
where domain_id = %(domain_or_interface_id)s and protein_id = %(protein_id)s
    and mutation_modeller = %(mutation)s;
"""

# Local interface
get_interface_mutation_local_sql = """\
select interface_id as domain_or_interface_id,
    model_filename_wt,
    chain_modeller,
    mutation_modeller
from elaspic_webserver.elaspic_interface_mutation_local
where protein_id = %(protein_id)s and mutation = %(mutation)s;
"""

update_interface_mutation_local_sql = """\
update elaspic_webserver.elaspic_interface_mutation_local mut
set mut.protbert_score = %(protbert_score)s,
    mut.proteinsolver_score = %(proteinsolver_score)s,
    mut.el2_score = %(el2_score)s,
    mut.el2_version = %(el2_version)s
where interface_id = %(domain_or_interface_id)s and protein_id = %(protein_id)s
    and mutation_modeller = %(mutation)s;
"""

# Database core
get_core_mutation_database_sql = """\
SELECT d.uniprot_domain_id as domain_or_interface_id,
    CONCAT(d.path_to_data, mut.model_filename_wt) as model_filename_wt,
    mut.chain_modeller,
    mut.mutation_modeller
FROM elaspic.uniprot_domain_mutation mut
JOIN elaspic.uniprot_domain d USING (uniprot_domain_id)
WHERE mut.uniprot_id = %(protein_id)s AND mutation = %(mutation)s;
"""

update_core_mutation_database_sql = """\
update elaspic.uniprot_domain_mutation mut
set mut.protbert_score = %(protbert_score)s,
    mut.proteinsolver_score = %(proteinsolver_score)s,
    mut.el2_score = %(el2_score)s,
    mut.el2_version = %(el2_version)s
where uniprot_domain_id = %(domain_or_interface_id)s and uniprot_id = %(protein_id)s
    and mutation_modeller = %(mutation)s;
"""

# Database interface
get_interface_mutation_database_sql = """\
SELECT d.uniprot_domain_pair_id as domain_or_interface_id,
    CONCAT(d.path_to_data, mut.model_filename_wt) as model_filename_wt,
    mut.chain_modeller,
    mut.mutation_modeller
FROM elaspic.uniprot_domain_pair_mutation mut
JOIN elaspic.uniprot_domain_pair d USING (uniprot_domain_pair_id)
WHERE mut.uniprot_id = %(protein_id)s AND mutation = %(mutation)s;
"""

update_interface_mutation_database_sql = """\
update elaspic.uniprot_domain_pair_mutation mut
set mut.protbert_score = %(protbert_score)s,
    mut.proteinsolver_score = %(proteinsolver_score)s,
    mut.el2_score = %(el2_score)s,
    mut.el2_version = %(el2_version)s
where uniprot_domain_pair_id = %(domain_or_interface_id)s and uniprot_id = %(protein_id)s
    and mutation_modeller = %(mutation)s;
"""


async def get_mutation_info(item: js.Item) -> List[MutationInfo]:
    args = item.args
    kwargs = {"protein_id": args["protein_id"], "mutation": _format_mutation(args["mutations"])}

    if args["job_type"] == "local":
        core_mutation_sql = get_core_mutation_local_sql
        interface_mutation_sql = get_interface_mutation_local_sql
    else:
        assert args["job_type"] == "database"
        core_mutation_sql = get_core_mutation_database_sql
        interface_mutation_sql = get_interface_mutation_database_sql

    async with js.WDBConnection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(core_mutation_sql, kwargs)
            core_mutation_values: List[Tuple[int, str, str, str]] = await cur.fetchall()

            await cur.execute(interface_mutation_sql, kwargs)
            interface_mutation_values: List[Tuple[int, str, str, str]] = await cur.fetchall()

    mutation_info_list = [
        MutationInfo(
            domain_or_interface_id=domain_id,
            structure_file=structure_file,
            chain_id=chain_id,
            mutation=mutation,
            protein_id=kwargs["protein_id"],
            coi=COI.CORE,
        )
        for (domain_id, structure_file, chain_id, mutation) in core_mutation_values
    ] + [
        MutationInfo(
            domain_or_interface_id=interface_id,
            structure_file=structure_file,
            chain_id=chain_id,
            mutation=mutation,
            protein_id=kwargs["protein_id"],
            coi=COI.INTERFACE,
        )
        for (interface_id, structure_file, chain_id, mutation) in interface_mutation_values
    ]

    logger.info(
        "Obtained the following mutation data for item %s (%s): %s",
        item,
        kwargs,
        mutation_info_list,
    )
    return mutation_info_list


async def update_mutation_scores(job_type: str, mutation_scores: List[MutationInfo]) -> None:
    if job_type not in ["local", "database"]:
        raise ValueError

    required_attributes = [
        "domain_or_interface_id",
        "protein_id",
        "mutation",
        "protbert_score",
        "proteinsolver_score",
        "el2_score",
        "el2_version",
    ]

    if job_type == "local":
        core_mutation_sql = update_core_mutation_local_sql
        interface_mutation_sql = update_interface_mutation_local_sql
    else:
        assert job_type == "database"
        core_mutation_sql = update_core_mutation_database_sql
        interface_mutation_sql = update_interface_mutation_database_sql

    async with js.WDBConnection() as conn:
        async with conn.cursor() as cur:
            for mutation_score in mutation_scores:
                if mutation_score.coi == COI.CORE:
                    update_mutation_sql = core_mutation_sql
                else:
                    update_mutation_sql = interface_mutation_sql

                attributes = {key: getattr(mutation_score, key) for key in required_attributes}
                await cur.execute(update_mutation_sql, attributes)
                if cur.rowcount != 1:
                    logger.error(
                        "Unexpected number of rows modified when updating database: %s "
                        "(job_type = %s, coi = %s, attributes = %s).",
                        cur.rowcount,
                        job_type,
                        mutation_score.coi.value,
                        attributes,
                    )
        await conn.commit()


def _format_mutation(mutation: str) -> str:
    assert "," not in mutation
    if "_" in mutation:
        mutation = mutation.split("_")[-1]
    return mutation
