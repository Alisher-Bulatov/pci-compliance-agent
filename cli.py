import argparse
import json
import requests
import time
import logging
from rich import print

logging.basicConfig(
    filename="cli.log", level=logging.INFO, format="%(asctime)s %(message)s"
)


def handle_stage(event):
    print(f"\n[bold blue]🟦 {event['label']}[/bold blue]\n")


def handle_token(event):
    print(event["text"], end="", flush=True)


def handle_tool_result(event):
    result = event["text"]
    print("\n\n[green]🟩 Tool Result:[/green]")
    if isinstance(result, dict):
        if result.get("status") == "error":
            print(f"[red]❌ Tool error: {result.get('message')}[/red]")
            if "details" in result:
                print("[yellow]   Validation issues:[/yellow]")
                for detail in result["details"]:
                    loc = ".".join(str(part) for part in detail.get("loc", []))
                    print(f"   → {loc}: {detail.get('msg')}")
        else:
            print(json.dumps(result, indent=2))
    else:
        print(str(result))


def handle_error(event):
    print(f"\n[red]❌ {event['message']}[/red]\n")


def handle_info(event):
    print(f"\n[yellow]ℹ️ {event['message']}[/yellow]\n")


event_handlers = {
    "stage": handle_stage,
    "token": handle_token,
    "tool_result": handle_tool_result,
    "error": handle_error,
    "info": handle_info,
}


def process_message(message: str):
    try:
        start = time.time()
        response = requests.post(
            "http://localhost:8000/ask_full",
            json={"message": message},
            stream=True,
            timeout=30,
        )

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
                logging.info(json.dumps(event))
            except json.JSONDecodeError as e:
                print(f"\n[red]❌ Failed to decode event line: {e}[/red]\n")

        print(f"\n⏱️ [dim]Response time: {time.time() - start:.2f} seconds[/dim]\n")

    except requests.RequestException as e:
        print(f"\n[red]❌ Request failed: {e}[/red]\n")


def parse_args():
    parser = argparse.ArgumentParser(description="PCI DSS Compliance CLI")
    parser.add_argument(
        "-m", "--message", type=str, help="Send a single query and exit"
    )
    return parser.parse_args()


def main():
    print("[bold cyan]🔹 PCI DSS Compliance CLI[/bold cyan]")
    args = parse_args()

    if args.message:
        process_message(args.message)
        return

    while True:
        try:
            message = input("> ")
            if message.lower() in {"exit", "quit"}:
                break
            process_message(message)
        except KeyboardInterrupt:
            print("\n[red]Exiting...[/red]")
            break


if __name__ == "__main__":
    main()
