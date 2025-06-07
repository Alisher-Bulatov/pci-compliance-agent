import json
import requests


def main():
    print("🔹 PCI DSS Compliance CLI")
    while True:
        message = input("> ")
        if message.lower() in {"exit", "quit"}:
            break

        try:
            response = requests.get(
                "http://localhost:8000/ask_full",
                params={"message": message},
                stream=True,
                timeout=10,
            )

            event_handlers = {
                "stage": lambda e: print(f"\n🟦 {e['label']}\n"),
                "token": lambda e: print(e["text"], end="", flush=True),
                "tool_result": lambda e: print(f"\n\n🟩 Tool Result:\n{e['text']}\n"),
                "error": lambda e: print(f"\n❌ {e['message']}\n"),
                "info": lambda e: print(f"\nℹ️ {e['message']}\n"),
            }

            for line in response.iter_lines(decode_unicode=True):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    event_type = event.get("type")
                    handler = event_handlers.get(
                        event_type, lambda e: print(f"\n⚠️ Unknown event type: {e}\n")
                    )
                    handler(event)
                except json.JSONDecodeError as e:
                    print(f"\n❌ Failed to decode event line: {e}\n")

            print()

        except requests.RequestException as e:
            print(f"\n❌ Request failed: {e}\n")


if __name__ == "__main__":
    main()
