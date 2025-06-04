import json
import requests
from agent.llm_wrapper import query_llm
from agent.tool_call_parser import extract_tool_call
from agent.prompt_formatter import format_prompt
from retrieval.retriever import PCIDocumentRetriever

def main():
    print("PCI DSS Compliance Agent")

    retriever = PCIDocumentRetriever()

    while True:
        user_input = input("> ")
        if user_input.lower() in ["exit", "quit"]:
            break

        # Perform RAG
        context_chunks = retriever.retrieve(user_input, k=3)
        context = "\n".join(context_chunks)

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

                response = requests.post("http://localhost:8000/tool_call", json=tool_call)
                print("→", response.json().get("result", response.text))
            except Exception as e:
                print("\n❌ Failed to parse TOOL_CALL or send to MCP.")
                print("Error:", str(e))

if __name__ == "__main__":
    main()
