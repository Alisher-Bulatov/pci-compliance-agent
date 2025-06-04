import json
import requests
from agent.llm_wrapper import query_llm
from agent.tool_call_parser import extract_tool_call
from agent.prompt_formatter import format_prompt
from retrieval.retriever import PCIDocumentRetriever

ALLOWED_TOOLS = {
    "get_requirement_text",
    "search_by_topic",
    "compare_requirements",
    "recommend_tool",
}

def format_tool_result(result):
    if isinstance(result, list):
        return "\n".join(
            f"Requirement {r['id']}: {r['text']} [tags: {', '.join(r.get('tags', []))}]"
            for r in result
        )
    return str(result)

def main():
    print("PCI DSS Compliance Agent")

    retriever = PCIDocumentRetriever()

    while True:
        user_input = input("> ")
        if user_input.lower() in ["exit", "quit"]:
            break

        # Perform RAG
        context_chunks = retriever.retrieve(user_input, k=3)
        context = "\n".join(
            f"Requirement {c['id']}: {c['text']} [tags: {', '.join(c.get('tags', []))}]"
            if isinstance(c, dict) else str(c)
            for c in context_chunks
        )

        prompt = format_prompt(user_input, context)

        print("\n=== Sending to LLM ===")

        stream = query_llm(prompt, stream=True)
        buffered = ""
        for token in stream:
            print(token, end="", flush=True)
            buffered += token
        print()

        if "TOOL_CALL" in buffered:
            try:
                tool_call = extract_tool_call(buffered)
                print("\nParsed TOOL_CALL:", tool_call)

                if tool_call["tool_name"] not in ALLOWED_TOOLS:
                    print(f"\n❌ Ignored unapproved tool call: {tool_call['tool_name']}")
                    continue

                response = requests.post("http://localhost:8000/tool_call", json=tool_call)
                result = response.json().get("result", response.text)

                if isinstance(result, dict) and "tool_name" in result:
                    delegated_tool = result.get("tool_name")
                    if delegated_tool in ALLOWED_TOOLS:
                        print("\n↪️ Tool issued a delegated TOOL_CALL\n")
                        response = requests.post("http://localhost:8000/tool_call", json=result)
                        result = response.json().get("result", response.text)
                    else:
                        print(f"\n❌ Delegated TOOL_CALL rejected: {delegated_tool}")
                        continue

                print("\n→ Tool Result:\n")
                print(format_tool_result(result))

                follow_up_prompt = format_prompt(
                    user_input=user_input,
                    context="",  # new context not needed
                    type="followup",
                    tool_result=format_tool_result(result),
                )

                print("\n=== Follow-up from LLM ===\n")
                for token in query_llm(follow_up_prompt, stream=True):
                    print(token, end="", flush=True)
                print()

            except Exception as e:
                print("\n❌ Failed to parse TOOL_CALL or send to MCP.")
                print("Error:", str(e))

if __name__ == "__main__":
    main()
