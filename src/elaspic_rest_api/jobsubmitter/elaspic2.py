from typing import Dict

import aiohttp

from elaspic_rest_api import jobsubmitter as js


async def elaspic2(ds: js.DataStructures) -> None:
    async with aiohttp.ClientSession() as session:
        while True:
            item = await ds.elaspic2_pending_queue.get()
            async with session.post(url, json={"test": "object"}):
                pass

            # Fun stuff
            js.remove_from_monitored(item, ds.monitored_jobs)


def extract_protein_info(item: js.Item) -> Dict:
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


def finalize_mutation(item: js.Item):
    args = item.args
    if args["job_type"] == "local":
        sql_command = SQL_COMMAND_LOCAL
    else:
        assert args["job_type"] == "database"
        sql_command = SQL_COMMAND_DATABASE
    sql_command = sql_command.format(protein_id=args["protein_id"], mutation=args["mutations"])


SQL_COMMAND_LOCAL = """\
LOCK TABLES muts AS web_muts WRITE,
            elaspic_core_mutation AS ecm READ,
            elaspic_core_mutation_local AS ecml READ,
            elaspic_interface_mutation AS eim READ,
            elaspic_interface_mutation_local eiml READ;

UPDATE muts web_muts
LEFT JOIN elaspic_core_mutation ecm ON (
    web_muts.protein = ecm.protein_id and web_muts.mut = ecm.mutation)
LEFT JOIN elaspic_core_mutation_local ecml ON (
    web_muts.protein = ecml.protein_id and web_muts.mut = ecml.mutation)
SET web_muts.affectedType='CO', web_muts.status='error', web_muts.dateFinished = now(),
    web_muts.error='1: ddG not calculated'
WHERE web_muts.protein = '{protein_id}' and web_muts.mut = '{mutation}' AND
      ecm.ddg IS NULL AND ecml.ddg IS NULL;

UPDATE muts web_muts
LEFT JOIN elaspic_core_mutation ecm ON (
    web_muts.protein = ecm.protein_id and web_muts.mut = ecm.mutation)
LEFT JOIN elaspic_core_mutation_local ecml ON (
    web_muts.protein = ecml.protein_id and web_muts.mut = ecml.mutation)
SET web_muts.affectedType='CO', web_muts.status='done', web_muts.dateFinished = now(),
    web_muts.error=Null
WHERE web_muts.protein = '{protein_id}' and web_muts.mut = '{mutation}' AND
    (ecm.ddg IS NOT NULL OR ecml.ddg IS NOT NULL);

UPDATE muts web_muts
LEFT JOIN elaspic_interface_mutation eim ON (
    web_muts.protein = eim.protein_id and web_muts.mut = eim.mutation)
LEFT JOIN elaspic_interface_mutation_local eiml ON (
    web_muts.protein = eiml.protein_id and web_muts.mut = eiml.mutation)
SET web_muts.affectedType='IN', web_muts.status='done', web_muts.dateFinished = now(),
    web_muts.error=Null
WHERE web_muts.protein = '{protein_id}' and web_muts.mut = '{mutation}' AND
    (eim.ddg IS NOT NULL OR eiml.ddg IS NOT NULL);

UNLOCK TABLES;
"""


SQL_COMMAND_DATABASE = """\
LOCK TABLES muts AS web_muts WRITE,
            elaspic_core_mutation AS ecm READ,
            elaspic_core_mutation_local AS ecml READ,
            elaspic_interface_mutation AS eim READ,
            elaspic_interface_mutation_local eiml READ;

UPDATE muts web_muts
LEFT JOIN elaspic_core_mutation ecm ON (
    web_muts.protein = ecm.protein_id and web_muts.mut = ecm.mutation)
LEFT JOIN elaspic_core_mutation_local ecml ON (
    web_muts.protein = ecml.protein_id and web_muts.mut = ecml.mutation)
SET web_muts.affectedType='CO', web_muts.status='error', web_muts.dateFinished = now(),
    web_muts.error='1: ddG not calculated'
WHERE web_muts.protein = '{protein_id}' and web_muts.mut = '{mutation}' AND
      ecm.ddg IS NULL AND ecml.ddg IS NULL;

UPDATE muts web_muts
LEFT JOIN elaspic_core_mutation ecm ON (
    web_muts.protein = ecm.protein_id and web_muts.mut = ecm.mutation)
LEFT JOIN elaspic_core_mutation_local ecml ON (
    web_muts.protein = ecml.protein_id and web_muts.mut = ecml.mutation)
SET web_muts.affectedType='CO', web_muts.status='done', web_muts.dateFinished = now(),
    web_muts.error=Null
WHERE web_muts.protein = '{protein_id}' and web_muts.mut = '{mutation}' AND
    (ecm.ddg IS NOT NULL OR ecml.ddg IS NOT NULL);

UPDATE muts web_muts
LEFT JOIN elaspic_interface_mutation eim ON (
    web_muts.protein = eim.protein_id and web_muts.mut = eim.mutation)
LEFT JOIN elaspic_interface_mutation_local eiml ON (
    web_muts.protein = eiml.protein_id and web_muts.mut = eiml.mutation)
SET web_muts.affectedType='IN', web_muts.status='done', web_muts.dateFinished = now(),
    web_muts.error=Null
WHERE web_muts.protein = '{protein_id}' and web_muts.mut = '{mutation}' AND
    (eim.ddg IS NOT NULL OR eiml.ddg IS NOT NULL);

UNLOCK TABLES;
"""
