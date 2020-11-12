from enum import Enum
from typing import Dict, List, NamedTuple, Tuple, Type

import aiohttp
from kmbio import PDB

from elaspic_rest_api import jobsubmitter as js

core_mutation_local_sql = """\
select model_filename_wt, chain_modeller, mutation_modeller
from elaspic_core_mutation_local
where protein_id = %(protein_id)s and mutation = %(mutation)s;
"""

interface_mutation_local_sql = """\
select model_filename_wt, chain_modeller, mutation_modeller
from elaspic_interface_mutation_local
where protein_id = %(protein_id)s and mutation = %(mutation)s;
"""

core_mutation_database_sql = """\
SELECT CONCAT(m.path_to_data, mut.model_filename_wt) as model_filename_wt,
mut.chain_modeller, mut.mutation_modeller
FROM elaspic_core_mutation mut
JOIN elaspic_core_model m USING (protein_id, domain_id)
WHERE protein_id = %(protein_id)s AND mutation = %(mutation)s;
"""

interface_mutation_database_sql = """\
SELECT CONCAT(m.path_to_data, mut.model_filename_wt) as model_filename_wt,
mut.chain_modeller, mut.mutation_modeller
FROM elaspic_interface_mutation mut
JOIN elaspic_interface_model m USING (interface_id)
WHERE protein_id = %(protein_id)s AND mutation = %(mutation)s;
"""


class COI(Enum):
    CORE = "core"
    INTERFACE = "interface"


class MutationInfo(NamedTuple):
    structure_file: str
    chain_id: str
    mutation: str
    coi: COI


class EL2Error(Exception):
    pass


async def elaspic2(ds: js.DataStructures) -> None:
    async with aiohttp.ClientSession() as session:
        while True:
            item = await ds.elaspic2_pending_queue.get()
            async with session.post(url, json={"test": "object"}):
                pass

            # Fun stuff
            js.remove_from_monitored(item, ds.monitored_jobs)


async def query_mutation_data(item: js.Item) -> List[MutationInfo]:
    args = item.args
    kwargs = {"protein_id": args["protein_id"], "mutation": args["mutations"]}
    assert "," not in kwargs["mutation"]

    if args["job_type"] == "database":
        core_mutation_sql = core_mutation_database_sql
        interface_mutation_sql = core_mutation_database_sql
    else:
        assert args["job_type"] == "local"
        core_mutation_sql = core_mutation_local_sql
        interface_mutation_sql = interface_mutation_local_sql

    async with js.WDBConnection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(core_mutation_sql, kwargs)
            core_mutation_values: List[Tuple[str, str, str]] = await cur.fetchall()

            await cur.execute(interface_mutation_sql, kwargs)
            interface_mutation_values: List[Tuple[str, str, str]] = await cur.fetchall()

    mutation_values = (
        #
        [MutationInfo(*values, COI.CORE) for values in core_mutation_values]
        + [MutationInfo(*values, COI.INTERFACE) for values in interface_mutation_values]
    )
    return mutation_values


def extract_protein_info(mutation_info: MutationInfo, remove_hetatms=True) -> Dict:
    structure = PDB.load(structure_file)
    unknown_residue_marker = "" if remove_hetatms else "X"

    protein_sequence = None
    ligand_sequence = None
    for chain in structure.chains:
        chain_sequence = structure_tools.get_chain_sequence(
            chain, if_unknown="replace", unknown_residue_marker=unknown_residue_marker
        )
        if chain.id == mutation_info.chain_id:
            protein_sequence = chain_sequence
        elif mutation_info.coi == COI.INTERFACE and ligand_sequence is None and chain_sequence:
            ligand_sequence = chain_sequence

    result = {
        "protein_structure_url": "",
        "protein_sequence": protein_sequence,
        "mutations": mutation_info.mutation,
    }

    if mutation_info.coi == COI.INTERFACE:
        result["ligand_sequence"] = ligand_sequence
    return result


def get_protein_info_local(item: js.Item):
    pass


def get_protein_info_database(item: js.Item):
    pass


def finalize_mutation_local(item: js.Item):
    pass
