import asyncio
import logging
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import aiohttp
from kmbio import PDB
from kmtools import structure_tools

from elaspic_rest_api import config
from elaspic_rest_api import jobsubmitter as js
from elaspic_rest_api.jobsubmitter.elaspic2db import get_mutation_info, update_mutation_scores
from elaspic_rest_api.jobsubmitter.elaspic2types import COI, EL2Error, MutationInfo

logger = logging.getLogger(__name__)


async def elaspic2_submit_loop(ds: js.DataStructures) -> None:
    elaspic2_jobs_api = urljoin(config.ELASPIC2_URL, "/jobs/")
    loop = asyncio.get_running_loop()
    executor = ProcessPoolExecutor(1)

    async with aiohttp.ClientSession() as session:
        while True:
            item = await ds.elaspic2_pending_queue.get()
            mutation_info_list = await get_mutation_info(item)
            mutation_info_list = await loop.run_in_executor(
                None, resolve_mutation_info, mutation_info_list
            )
            protein_info_list = await loop.run_in_executor(
                executor, extract_protein_info_list, mutation_info_list
            )

            item.el2_mutation_info_list = []
            for mutation_info, protein_info in zip(mutation_info_list, protein_info_list):
                async with session.post(elaspic2_jobs_api, json=protein_info) as resp:
                    job_request = await resp.json()
                mutation_info = mutation_info._replace(el2_web_url=job_request["web_url"])
                item.el2_mutation_info_list.append(mutation_info)
            await ds.elaspic2_running_queue.put(item)


async def elaspic2_collect_loop(ds: js.DataStructures) -> None:
    async with aiohttp.ClientSession() as session:
        while True:
            for _ in range(ds.elaspic2_running_queue.qsize()):
                item = await ds.elaspic2_running_queue.get()

                mutation_scores = []
                is_finished = True
                for mutation_info in item.el2_mutation_info_list:
                    async with session.get(mutation_info.el2_web_url) as resp:
                        try:
                            job_status = await resp.json()
                        except Exception as e:
                            logger.error("Failed to retrieve ELASPIC2 status with error: %s.", e)
                            is_finished = False
                            break
                    if job_status["status"] not in ["error", "success"]:
                        is_finished = False
                        break
                    async with session.get(job_status["web_url"]) as resp:
                        try:
                            job_result = await resp.json()
                        except Exception as e:
                            logger.error("Failed to retrieve ELASPIC2 status with error: %s.", e)
                            is_finished = False
                            break
                    mutation_score = job_result_to_mutation_scores(mutation_info, job_result[0])
                    mutation_scores.append(mutation_score)

                if not is_finished:
                    await ds.elaspic2_running_queue.put(item)
                    continue

                for mutation_info in item.el2_mutation_info_list:
                    await session.delete(mutation_info.el2_web_url)

                await update_mutation_scores(item.args["job_type"], mutation_scores)
                await js.finalize_mutation(item)
                await js.remove_from_monitored(item, ds.monitored_jobs)
            await asyncio.sleep(30)


def job_result_to_mutation_scores(mutation_info: MutationInfo, job_result: Dict) -> MutationInfo:
    if mutation_info.coi == COI.CORE:
        return mutation_info._replace(
            protbert_score=job_result["protbert_core"],
            proteinsolver_score=job_result["proteinsolver_core"],
            el2_score=job_result["el2core"],
        )
    else:
        return mutation_info._replace(
            protbert_score=job_result["protbert_interface"],
            proteinsolver_score=job_result["proteinsolver_interface"],
            el2_score=job_result["el2interface"],
        )


def resolve_mutation_info(mutation_info_list: List[MutationInfo]) -> List[MutationInfo]:
    data_dir = Path(config.DATA_DIR)
    mutation_info_list_resolved = []
    for mutation_info in mutation_info_list:
        mutation_info = mutation_info._replace(
            structure_file=data_dir.joinpath(mutation_info.structure_file).resolve().as_posix()
        )
        mutation_info_list_resolved.append(mutation_info)
    return mutation_info_list_resolved


def extract_protein_info_list(mutation_info_list: List[MutationInfo]) -> List[Dict]:
    protein_info_list = []
    for mutation_info in mutation_info_list:
        protein_info = extract_protein_info(mutation_info)
        protein_info_list.append(protein_info)
    return protein_info_list


def extract_protein_info(mutation_info: MutationInfo) -> Dict:
    structure_file = Path(mutation_info.structure_file)

    if not structure_file.is_file():
        raise EL2Error(f"Could not find structure for mutation: {mutation_info}.")
    if config.DATA_DIR not in structure_file.as_posix():
        raise EL2Error(f"Structure file is not available remotely for mutation: {mutation_info}.")

    @contextmanager
    def disable_logger(logger, level=logging.WARNING):
        try:
            logger.setLevel(level)
            yield
        finally:
            logger.setLevel(logging.NOTSET)

    with disable_logger(logging.getLogger("kmbio.PDB.core.atom")):
        structure = PDB.load(structure_file)

    protein_sequence, ligand_sequence = _extract_chain_sequences(
        structure, mutation_info.chain_id, mutation_info.coi
    )

    if protein_sequence is None:
        raise EL2Error(f"Could not extract protein sequence for mutation: {mutation_info}.")
    if mutation_info.coi == COI.INTERFACE and ligand_sequence is None:
        raise EL2Error(f"Could not extract ligand sequence for mutation: {mutation_info}.")
    if protein_sequence[int(mutation_info.mutation[1:-1]) - 1] != mutation_info.mutation[0]:
        raise EL2Error(f"Mutation does not match extracted protein sequence: {mutation_info}.")

    structure_file_url = urljoin(
        config.SITE_URL,
        Path(config.SITE_DATA_DIR).joinpath(structure_file.relative_to(config.DATA_DIR)).as_posix(),
    )
    result = {
        **{
            "protein_structure_url": structure_file_url,
            "protein_sequence": protein_sequence,
            "mutations": map_mutation_to_chain(
                structure, mutation_info.chain_id, mutation_info.mutation
            ),
        },
        **({"ligand_sequence": ligand_sequence} if ligand_sequence is not None else {}),
    }

    return result


def _extract_chain_sequences(
    structure: PDB.Structure, chain_id: str, coi: COI, remove_hetatms=True
) -> Tuple[Optional[str], Optional[str]]:
    unknown_residue_marker = "" if remove_hetatms else "X"
    protein_sequence = None
    ligand_sequence = None
    for chain in structure.chains:
        chain_sequence = structure_tools.get_chain_sequence(
            chain, if_unknown="replace", unknown_residue_marker=unknown_residue_marker
        )
        if chain.id == chain_id:
            protein_sequence = chain_sequence
        elif coi == COI.INTERFACE and ligand_sequence is None and chain_sequence:
            ligand_sequence = chain_sequence
    return protein_sequence, ligand_sequence


def map_mutation_to_chain(structure: PDB.Structure, chain_id: str, mutation: str) -> str:
    df = structure.to_dataframe()
    chain_df = df[df["chain_id"] == chain_id]

    residue_idx_map = {
        old_residue_idx: new_residue_idx
        for (old_residue_idx, new_residue_idx) in zip(
            chain_df["residue_idx"], chain_df["residue_idx"] - chain_df["residue_idx"].min()
        )
    }

    pos = int(mutation[1:-1])
    pos_new = residue_idx_map[pos - 1] + 1
    return f"{mutation[0]}{pos_new}{mutation[-1]}"
