import json
import time
import requests


def _handle_streaming_response(response):
    for line in response.iter_lines():
        if line:
            data = json.loads(line.decode("utf-8"))
            token = data.get("response", "")
            if token:
                yield token


def query_llm(
    prompt: str, stream: bool = True, timeout: int = 10, max_retries: int = 3
):
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "mistral:7b-instruct-v0.3-q4_K_M",
        "prompt": prompt,
        "stream": stream,
        "options": {"temperature": 0.3, "num_predict": 400},
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, json=payload, stream=stream, timeout=timeout)
            response.raise_for_status()

            if stream:
                yield from _handle_streaming_response(response)
                return ""

            return response.json().get("response", "")

        except requests.RequestException as e:
            print(f"⚠️ LLM request failed (attempt {attempt}/{max_retries}): {e}")
            if attempt == max_retries:
                return "" if not stream else ""
            time.sleep(2**attempt)
