from enum import Enum
from typing import Dict, List, Tuple, Type

import aiohttp
from kmbio import PDB

from elaspic_rest_api import jobsubmitter as js

mutation_sql = """\
select model_filename_wt, chain_modeller, mutation_modeller
from elaspic_webserver.elaspic_core_mutation_local
where protein_id = %(protein_id)s and mutation = %(mutation)s;
"""


class COI(Enum):
    CORE = "core"
    INTERFACE = "interface"


async def elaspic2(ds: js.DataStructures) -> None:
    async with aiohttp.ClientSession() as session:
        while True:
            item = await ds.elaspic2_pending_queue.get()
            async with session.post(url, json={"test": "object"}):
                pass

            # Fun stuff
            js.remove_from_monitored(item, ds.monitored_jobs)


async def query_mutation_data(item: js.Item) -> List[Tuple[str, str, str, COI]]:
    args = item.args
    DBConnection: Type[js.db._DBConnection]

    if args["job_type"] == "database":
        DBConnection = js.EDBConnection
        core_mutation_table = "elaspic.elaspic_domain_mutation"
        interface_mutation_table = "elaspic.elaspic_domain_pair_mutation"
    else:
        assert args["job_type"] == "local"
        DBConnection = js.WDBConnection
        core_mutation_table = "elaspic_webserver.elaspic_core_mutation_local"
        interface_mutation_table = "elaspic_webserver.elaspic_interface_mutation_local"

    kwargs = {"protein_id": args["protein_id"], "mutation": args["mutations"]}
    assert "," not in kwargs["mutation"]

    async with DBConnection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(mutation_sql.format(mutation_table=core_mutation_table), kwargs)
            core_mutation_values = await cur.fetchall()

            await cur.execute(mutation_sql.format(mutation_table=interface_mutation_table), kwargs)
            interface_mutation_values = await cur.fetchall()

    mutation_values = (
        #
        [tuple(values) + (COI.CORE,) for values in core_mutation_values]
        + [tuple(values) + (COI.INTERFACE,) for values in interface_mutation_values]
    )
    return mutation_values  # type: ignore


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
