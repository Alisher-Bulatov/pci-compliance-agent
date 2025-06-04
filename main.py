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
        llm_output = query_llm(prompt)

        if "TOOL_CALL" in llm_output:
            try:
                tool_call = extract_tool_call(llm_output)
                print("Parsed TOOL_CALL:", tool_call)

                response = requests.post("http://localhost:8000/tool_call", json=tool_call)
                print("→", response.json().get("result", response.text))
            except Exception as e:
                print("\n❌ Failed to parse TOOL_CALL or send to MCP.")
                print("Error:", str(e))
        else:
            print("\n🧠 Response:")
            print(llm_output.strip())

if __name__ == "__main__":
    main()
