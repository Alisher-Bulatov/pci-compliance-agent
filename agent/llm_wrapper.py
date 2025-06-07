import json
from typing import Generator, Union

import requests


def stream_response(response) -> Generator[str, None, None]:
    for line in response.iter_lines():
        if line:
            data = json.loads(line.decode("utf-8"))
            token = data.get("response", "")
            if token:
                yield token


def query_llm(
    prompt: str,
    stream: bool = True,
    timeout: int = 10,
    max_retries: int = 3,
) -> Union[str, Generator[str, None, None]]:
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "mistral:7b-instruct-v0.3-q4_K_M",
        "prompt": prompt,
        "stream": stream,
        "options": {"temperature": 0.3, "num_predict": 400},
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, stream=stream, timeout=timeout)
            response.raise_for_status()

            if stream:
                return stream_response(response)

            return response.json().get("response", "")

        except requests.RequestException as e:
            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"LLM query failed after {max_retries} attempts: {e}"
                ) from e

    return ""
