import requests
import json

def query_llm(prompt: str, stream: bool = True):
    if not stream:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral:7b-instruct-v0.3-q4_K_M",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 400
                }
            }
        )
        return response.json().get("response", "")

    # Streaming version
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "mistral:7b-instruct-v0.3-q4_K_M",
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": 0.3,
                "num_predict": 400
            }
        },
        stream=True
    )

    for line in response.iter_lines():
        if line:
            data = json.loads(line.decode("utf-8"))
            token = data.get("response", "")
            yield token
