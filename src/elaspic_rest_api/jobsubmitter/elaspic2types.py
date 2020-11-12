from enum import Enum
from typing import NamedTuple, Optional


class COI(Enum):
    CORE = "core"
    INTERFACE = "interface"


class MutationInfo(NamedTuple):
    domain_or_interface_id: int
    structure_file: str
    chain_id: str
    mutation: str
    coi: COI
    el2_web_url: Optional[str] = None


class MutationScores(NamedTuple):
    protbert_score: float
    proteinsolver_score: float
    el2_score: float
    el2_version: str = "0.1.13"


class EL2Error(Exception):
    pass
