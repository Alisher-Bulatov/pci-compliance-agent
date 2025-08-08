from typing import List
from pydantic import BaseModel
from agent.models.base import BaseToolOutputSchema


class RequirementEntry(BaseModel):
    id: str
    text: str
    tags: List[str]


class RequirementOutput(BaseToolOutputSchema):
    result: List[RequirementEntry]

