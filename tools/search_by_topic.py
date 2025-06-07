"""Search for PCI DSS requirements related to a specific topic or keyword."""

from typing import Literal

from pydantic import BaseModel

from retrieval.retriever import PCIDocumentRetriever
from agent.models.requirement import RequirementEntry, RequirementOutput


class InputSchema(BaseModel):
    query: str


class OutputSchema(RequirementOutput):
    tool_name: Literal["search_by_topic"]


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
