from retrieval.retriever import PCIDocumentRetriever

TOP_K = 10


def extract_query_tags(query):
    lowered = query.lower()
    tags = []
    if any(word in lowered for word in ["encrypt", "crypto", "key"]):
        tags.append("encryption")
    if any(word in lowered for word in ["auth", "password", "login"]):
        tags.append("authentication")
    if any(word in lowered for word in ["store", "retain", "database"]):
        tags.append("storage")
    if any(word in lowered for word in ["firewall", "network", "router"]):
        tags.append("network")
    if "compliance" in lowered or "audit" in lowered:
        tags.append("compliance")
    return tags


def main(query):
    retriever = PCIDocumentRetriever()
    results = retriever.retrieve(query, k=TOP_K)

    query_tags = set(extract_query_tags(query))
    candidates = []

    for entry in results:
        entry_tags = set(entry.get("tags", []))
        overlap_score = len(entry_tags & query_tags)
        candidates.append((entry, overlap_score))

    candidates.sort(key=lambda x: x[1], reverse=True)

    return [
        {"id": entry["id"], "text": entry["text"], "tags": entry["tags"]}
        for entry, _ in candidates[:5]
    ]
