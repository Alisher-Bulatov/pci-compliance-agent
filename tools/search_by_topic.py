from typing import List, Literal

from pydantic import BaseModel

from retrieval.retriever import PCIDocumentRetriever
from agent.tool_schema import BaseToolOutputSchema


class InputSchema(BaseModel):
    query: str


class RequirementEntry(BaseModel):
    id: str
    text: str
    tags: List[str]


class OutputSchema(BaseToolOutputSchema):
    tool_name: Literal["search_by_topic"]
    result: List[RequirementEntry]


retriever = PCIDocumentRetriever()


def main(input_data: InputSchema) -> OutputSchema:
    """Perform vector search on PCI DSS chunks based on query string."""
    chunks = retriever.retrieve(input_data.query, k=3)
    entries = [
        RequirementEntry(
            id=c["id"],
            text=c["text"],
            tags=c.get("tags", []),
        )
        for c in chunks
    ]

    return OutputSchema(tool_name="search_by_topic", result=entries)
