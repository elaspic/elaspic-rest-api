from typing import List, Optional

from pydantic import BaseModel


class Mutations(BaseModel):
    protein_id: str
    structure_file: Optional[str]
    sequence_file: Optional[str]
    mutations: str
    uniprot_domain_pair_ids: Optional[str]


class DataIn(BaseModel):
    api_token: str
    job_id: str
    job_type: str
    job_email: Optional[str]
    mutations: List[Mutations]

    class Config:
        schema_extra = {
            "example": {
                "api_token": "XXXXX",
                "job_id": "1abcde",
                "job_type": "database",
                "mutations": [
                    {
                        "mutations": "G49V,G49A,G49L,G49I,G49C,G49M,G49F,G49W,G49P",
                        "protein_id": "P21397",
                        "uniprot_domain_pair_ids": "",
                    }
                ],
            }
        }
