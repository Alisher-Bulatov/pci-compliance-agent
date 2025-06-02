import requests

def query_llm(prompt: str) -> str:
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