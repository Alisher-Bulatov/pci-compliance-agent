import requests


def main(requirement_ids):
    if not isinstance(requirement_ids, list) or len(requirement_ids) < 2:
        return {"error": "Please provide at least two requirement IDs to compare."}

    results = []

    for req_id in requirement_ids:
        try:
            response = requests.post(
                "http://localhost:8000/tool_call",
                json={
                    "tool_name": "get_requirement_text",
                    "tool_input": {"requirement_id": req_id},
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json().get("result", {})

            results.append(
                {
                    "id": req_id,
                    "text": data.get("text", "Unavailable"),
                    "tags": data.get("tags", []),
                }
            )

        except requests.RequestException as e:
            results.append(
                {"id": req_id, "text": f"❌ Failed to fetch: {e}", "tags": []}
            )

    return results
