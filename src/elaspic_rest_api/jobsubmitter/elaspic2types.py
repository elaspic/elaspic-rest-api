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
    protein_id: str
    coi: COI
    # Results
    el2_web_url: Optional[str] = None
    protbert_score: Optional[float] = None
    proteinsolver_score: Optional[float] = None
    el2_score: Optional[float] = None
    el2_version: str = "0.1.13"


class EL2Error(Exception):
    pass
