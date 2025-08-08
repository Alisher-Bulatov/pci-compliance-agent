# agent/llm_wrapper.py
import json
import os
from typing import AsyncGenerator, Union
import httpx


def get_env(var_name: str, default: str) -> str:
    return os.getenv(var_name, default)


LLM_API_URL = get_env("LLM_API_URL", "http://localhost:11434/api/generate")
LLM_MODEL = get_env("LLM_MODEL", "qwen2.5:7b-instruct")


async def query_llm(
    prompt: str,
    stream: bool = True,
    timeout: int = 10,
    max_retries: int = 3,
) -> Union[str, AsyncGenerator[str, None]]:
    payload = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": stream,
        "options": {"temperature": 0.3, "num_predict": 400},
    }

    if not stream:
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.post(LLM_API_URL, json=payload)
                    response.raise_for_status()
                    return (await response.json()).get("response", "")
                except httpx.RequestError as e:
                    if attempt == max_retries - 1:
                        raise RuntimeError(
                            f"LLM query failed after {max_retries} attempts: {e}"
                        ) from e
        return ""

    async def token_generator() -> AsyncGenerator[str, None]:
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    async with client.stream(
                        "POST", LLM_API_URL, json=payload
                    ) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if line:
                                data = json.loads(line)
                                token = data.get("response", "")
                                if token:
                                    yield token
                break
            except httpx.RequestError as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(
                        f"LLM stream failed after {max_retries} attempts: {e}"
                    ) from e

    return token_generator()
