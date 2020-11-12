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
    chain: str
    mutation: str
    coi: COI


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


def extract_protein_info(structure_file: str, chain: str, mutation: str, coi: COI) -> Dict:
    structure = PDB.load(structure_file)

    out = {
        "protein_structure_url": "https://files.rcsb.org/download/1MFG.pdb",
        "protein_sequence": (
            "GSMEIRVRVEKDPELGFSISGGVGGRGNPFRPDDDGIFVTRVQPEGPASKLLQPGDKIIQANGYSFINI"
            "EHGQAVSLLKTFQNTVELIIVREVSS"
        ),
        "mutations": "G1A,G1C",
        "ligand_sequence": "EYLGLDVPV",
    }


def get_protein_info_local(item: js.Item):
    pass


def get_protein_info_database(item: js.Item):
    pass


def finalize_mutation_local(item: js.Item):
    pass
