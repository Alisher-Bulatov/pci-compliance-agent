from pydantic import BaseModel
from typing import Any


class BaseToolOutputSchema(BaseModel):
    def serialized_result(self) -> Any:
        if isinstance(self.result, list):
            return [r.dict() if hasattr(r, "dict") else r for r in self.result]
        if hasattr(self.result, "dict"):
            return self.result.dict()
        return self.result
