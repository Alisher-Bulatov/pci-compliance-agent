# agent/llm_wrapper.py
import json
from typing import AsyncGenerator, Union
import httpx


async def query_llm(
    prompt: str,
    stream: bool = True,
    timeout: int = 10,
    max_retries: int = 3,
) -> Union[str, AsyncGenerator[str, None]]:
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "mistral:7b-instruct-v0.3-q4_K_M",
        "prompt": prompt,
        "stream": stream,
        "options": {"temperature": 0.3, "num_predict": 400},
    }

    if not stream:
        # Non-streaming: simple POST
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    return (await response.json()).get("response", "")
                except httpx.RequestError as e:
                    if attempt == max_retries - 1:
                        raise RuntimeError(
                            f"LLM query failed after {max_retries} attempts: {e}"
                        ) from e
        return ""

    # Streaming path: define generator inside the client scope
    async def token_generator() -> AsyncGenerator[str, None]:
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    async with client.stream("POST", url, json=payload) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if line:
                                data = json.loads(line)
                                token = data.get("response", "")
                                if token:
                                    yield token
                break  # if successful, exit retry loop
            except httpx.RequestError as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(
                        f"LLM stream failed after {max_retries} attempts: {e}"
                    ) from e

    return token_generator()
