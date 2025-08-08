import argparse
import json
import os
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


def process_message(message: str, use_mock=False):
    try:
        start = time.time()
        url = (
            f"{os.getenv('MCP_API_URL', 'http://localhost:8000')}/ask_mock_full"
            if use_mock
            else f"{os.getenv('MCP_API_URL', 'http://localhost:8000')}/ask_full"
        )
        response = requests.post(
            url,
            json={"message": message},
            stream=True,
            timeout=30,
        )
        response.raise_for_status()

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

    except requests.HTTPError as e:
        print(f"\n[red]❌ HTTP error: {e}[/red]\n")
    except requests.RequestException as e:
        print(f"\n[red]❌ Request failed: {e}[/red]\n")


def parse_args():
    parser = argparse.ArgumentParser(description="PCI DSS Compliance CLI")
    parser.add_argument(
        "-m", "--message", type=str, help="Send a single query and exit"
    )
    parser.add_argument(
        "--mock", action="store_true", help="Use mock endpoint instead of live"
    )
    return parser.parse_args()


def main():
    print("[bold cyan]🔹 PCI DSS Compliance CLI[/bold cyan]")
    args = parse_args()

    if args.message:
        process_message(args.message, use_mock=args.mock)
        return

    while True:
        try:
            message = input("> ")
            if message.lower() in {"exit", "quit"}:
                break
            process_message(message, use_mock=args.mock)
        except KeyboardInterrupt:
            print("\n[red]Exiting...[/red]")
            break


if __name__ == "__main__":
    main()

