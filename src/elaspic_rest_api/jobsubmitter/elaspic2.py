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
