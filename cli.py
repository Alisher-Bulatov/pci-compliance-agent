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
                timeout=15,
            )

            def handle_stage(event):
                print(f"\n🟦 {event['label']}\n")

            def handle_token(event):
                print(event["text"], end="", flush=True)

            def handle_tool_result(event):
                result = event["text"]

                print("\n\n🟩 Tool Result:")
                if isinstance(result, dict):
                    if result.get("status") == "error":
                        print(f"❌ Tool error: {result.get('message')}")
                        if "details" in result:
                            print("   Validation issues:")
                            for detail in result["details"]:
                                loc = ".".join(
                                    str(part) for part in detail.get("loc", [])
                                )
                                print(f"   → {loc}: {detail.get('msg')}")
                    else:
                        print(json.dumps(result, indent=2))
                else:
                    print(str(result))

            def handle_error(event):
                print(f"\n❌ {event['message']}\n")

            def handle_info(event):
                print(f"\nℹ️ {event['message']}\n")

            event_handlers = {
                "stage": handle_stage,
                "token": handle_token,
                "tool_result": handle_tool_result,
                "error": handle_error,
                "info": handle_info,
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

            print()  # spacing between interactions

        except requests.RequestException as e:
            print(f"\n❌ Request failed: {e}\n")


if __name__ == "__main__":
    main()
