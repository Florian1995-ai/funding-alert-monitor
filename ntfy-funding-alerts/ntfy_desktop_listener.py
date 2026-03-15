#!/usr/bin/env python3
"""
ntfy Desktop Listener — native Windows/Mac desktop notifications for funding alerts.

Connects to your local ntfy server via Server-Sent Events (SSE) and shows
native desktop notifications that work even when the browser is closed.

Usage:
    python ntfy_desktop_listener.py
    python ntfy_desktop_listener.py --topic jorge-funding
    python ntfy_desktop_listener.py --server http://localhost:8080
    python ntfy_desktop_listener.py --startup-install

Requirements:
    pip install plyer requests
"""

import os
import sys
import json
import argparse
import webbrowser
import time
from pathlib import Path

import requests

try:
    from plyer import notification as toast
except ImportError:
    print("[ERROR] Install plyer: pip install plyer")
    print("        This provides native desktop notifications.")
    sys.exit(1)

DEFAULT_SERVER = "http://localhost:8080"
DEFAULT_TOPIC = "jorge-funding"


def show_toast(title: str, message: str, click_url: str = None, timeout: int = 30):
    """Show a native desktop notification."""
    try:
        toast.notify(
            title=title,
            message=message,
            app_name="Funding Alerts",
            timeout=timeout,
        )
        if click_url:
            print(f"  Report: {click_url}")
    except Exception as e:
        print(f"  [TOAST ERROR] {e}")


def parse_actions(actions_str: str) -> dict:
    """Parse ntfy action buttons into a dict of label -> URL."""
    result = {}
    if not actions_str:
        return result
    for action in actions_str.split(";"):
        parts = [p.strip() for p in action.split(",")]
        if len(parts) >= 3 and parts[0] == "view":
            result[parts[1]] = parts[2]
    return result


def listen(server: str, topic: str):
    """Connect to ntfy SSE stream and show notifications."""
    url = f"{server}/{topic}/sse"
    print(f"[LISTENING] {url}")
    print(f"[INFO] Native desktop notifications active. Press Ctrl+C to stop.\n")

    while True:
        try:
            with requests.get(url, stream=True, timeout=None) as resp:
                if not resp.ok:
                    print(f"[ERROR] HTTP {resp.status_code} from ntfy")
                    time.sleep(10)
                    continue

                for line in resp.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue

                    try:
                        data = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue

                    if data.get("event") in ("open", "keepalive"):
                        if data.get("event") == "open":
                            print("[CONNECTED] Waiting for funding alerts...\n")
                        continue

                    # Real notification
                    title = data.get("title", data.get("topic", "Alert"))
                    message = data.get("message", "")
                    click_url = data.get("click", "")

                    # Parse action buttons for URLs
                    actions = parse_actions(data.get("actions", ""))
                    report_url = actions.get("Open Report", "")

                    print(f"[ALERT] {title}")
                    print(f"  {message[:100]}")

                    # Show native desktop toast
                    show_toast(
                        title=title,
                        message=message[:256],
                        click_url=report_url or click_url,
                    )

                    # Auto-open the report in browser if available
                    if report_url:
                        print(f"  [AUTO-OPEN] {report_url}")
                        webbrowser.open(report_url)

                    print()

        except requests.exceptions.ConnectionError:
            print("[RECONNECT] Connection lost, retrying in 5s...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n[STOPPED] Listener shut down.")
            sys.exit(0)
        except Exception as e:
            print(f"[ERROR] {e}, retrying in 10s...")
            time.sleep(10)


def install_startup(server: str, topic: str):
    """Add this script to Windows Startup folder."""
    startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    if not startup_dir.exists():
        print(f"[ERROR] Startup folder not found: {startup_dir}")
        return False

    script_path = Path(__file__).resolve()
    python_path = sys.executable

    bat_path = startup_dir / "ntfy_funding_alerts.bat"
    bat_content = f'@echo off\nstart /min "" "{python_path}" "{script_path}" --server {server} --topic {topic}\n'

    bat_path.write_text(bat_content, encoding="utf-8")
    print(f"[OK] Startup shortcut created: {bat_path}")
    print(f"[INFO] Funding alerts will auto-start when Windows boots.")
    print(f"[INFO] To remove: delete {bat_path}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Desktop notifications for funding alerts")
    parser.add_argument("--server", "-s", default=DEFAULT_SERVER,
                        help=f"ntfy server URL (default: {DEFAULT_SERVER})")
    parser.add_argument("--topic", "-t", default=DEFAULT_TOPIC,
                        help=f"ntfy topic to listen to (default: {DEFAULT_TOPIC})")
    parser.add_argument("--startup-install", action="store_true",
                        help="Add to Windows Startup for auto-start on boot")

    args = parser.parse_args()

    if args.startup_install:
        install_startup(args.server, args.topic)
        return

    listen(args.server, args.topic)


if __name__ == "__main__":
    main()
