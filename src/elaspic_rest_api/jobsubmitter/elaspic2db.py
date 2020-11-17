import logging
from typing import List, Tuple

from elaspic_rest_api import jobsubmitter as js
from elaspic_rest_api.jobsubmitter.elaspic2types import COI, MutationInfo, MutationScores

logger = logging.getLogger(__name__)

# Local core
get_core_mutation_local_sql = """\
select domain_id, model_filename_wt, chain_modeller, mutation_modeller
from elaspic_webserver.elaspic_core_mutation_local
where protein_id = %(protein_id)s and mutation = %(mutation)s;
"""

update_core_mutation_local_sql = """\
update elaspic_webserver.elaspic_core_mutation_local mut
set mut.protbert_core = %(protbert_score)s,
    mut.proteinsolver_core = %(proteinsolver_score)s,
    mut.el2core = %(elaspic2_score)s,
    mut.el2_version = %(elaspic2_version)s
where domain_id = %(domain_or_interface_id)s and protein_id = %(protein_id)s
    and mutation = %(mutation)s;
"""

# Local interface
get_interface_mutation_local_sql = """\
select interface_id, model_filename_wt, chain_modeller, mutation_modeller
from elaspic_webserver.elaspic_interface_mutation_local
where protein_id = %(protein_id)s and mutation = %(mutation)s;
"""

update_interface_mutation_local_sql = """\
update elaspic_webserver.elaspic_interface_mutation_local mut
set mut.protbert_core = %(protbert_score)s,
    mut.proteinsolver_core = %(proteinsolver_score)s,
    mut.el2core = %(elaspic2_score)s,
    mut.el2_version = %(elaspic2_version)s
where interface_id = %(domain_or_interface_id)s and protein_id = %(protein_id)s
    and mutation = %(mutation)s;
"""

# Database core
get_core_mutation_database_sql = """\
SELECT d.uniprot_domain_id, CONCAT(d.path_to_data, mut.model_filename_wt) as model_filename_wt,
mut.chain_modeller, mut.mutation_modeller
FROM elaspic.uniprot_domain_mutation mut
JOIN elaspic.uniprot_domain d USING (uniprot_domain_id)
WHERE mut.uniprot_id = %(protein_id)s AND mutation = %(mutation)s;
"""

update_core_mutation_database_sql = """\
update elaspic.uniprot_domain_mutation mut
set mut.protbert_core = %(protbert_score)s,
    mut.proteinsolver_core = %(proteinsolver_score)s,
    mut.el2core = %(elaspic2_score)s,
    mut.el2_version = %(elaspic2_version)s
where uniprot_domain_id = %(domain_or_interface_id)s and uniprot_id = %(protein_id)s
    and mutation = %(mutation)s;
"""

# Database interface
get_interface_mutation_database_sql = """\
SELECT d.uniprot_domain_pair_id, CONCAT(d.path_to_data, mut.model_filename_wt) as model_filename_wt,
mut.chain_modeller, mut.mutation_modeller
FROM elaspic.uniprot_domain_pair_mutation mut
JOIN elaspic.uniprot_domain_pair d USING (uniprot_domain_pair_id)
WHERE mut.uniprot_id = %(protein_id)s AND mutation = %(mutation)s;
"""

update_interface_mutation_database_sql = """\
update elaspic.uniprot_domain_pair_mutation mut
set mut.protbert_core = %(protbert_score)s,
    mut.proteinsolver_core = %(proteinsolver_score)s,
    mut.el2core = %(elaspic2_score)s,
    mut.el2_version = %(elaspic2_version)s
where uniprot_domain_pair_id = %(domain_or_interface_id)s and protein_id = %(protein_id)s
    and mutation = %(mutation)s;
"""


async def get_mutation_info(item: js.Item) -> List[MutationInfo]:
    args = item.args
    kwargs = {"protein_id": args["protein_id"], "mutation": args["mutations"]}
    assert "," not in kwargs["mutation"]

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

    mutation_info_list = (
        #
        [MutationInfo(*values, COI.CORE) for values in core_mutation_values]
        + [MutationInfo(*values, COI.INTERFACE) for values in interface_mutation_values]
    )
    return mutation_info_list


async def update_mutation_scores(item: js.Item, mutation_scores: List[MutationScores]) -> None:
    args = item.args
    kwargs = {"protein_id": args["protein_id"], "mutation": args["mutations"]}
    assert "," not in kwargs["mutation"]

    if args["job_type"] == "local":
        core_mutation_sql = update_core_mutation_local_sql
        interface_mutation_sql = update_interface_mutation_local_sql
    else:
        assert args["job_type"] == "database"
        core_mutation_sql = update_core_mutation_database_sql
        interface_mutation_sql = update_interface_mutation_database_sql

    async with js.WDBConnection() as conn:
        async with conn.cursor() as cur:
            for mutation_score in mutation_scores:
                await cur.execute(core_mutation_sql, {**kwargs, **mutation_score._asdict()})
                row_count = await cur.rowcount()
                if row_count != 1:
                    logger.error(
                        "Unexpected number of rows modified when updating database: %s.", row_count
                    )

                await cur.execute(interface_mutation_sql, {**kwargs, **mutation_score._asdict()})
                row_count = await cur.rowcount()
                if row_count != 1:
                    logger.error(
                        "Unexpected number of rows modified when updating database: %s.", row_count
                    )