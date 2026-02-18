#!/usr/bin/env python3

import json
import subprocess
import sys


def _prepare_notification_text(text: str) -> str:
    if not text:
        return ""
    # Replace control characters (including newlines) with spaces.
    cleaned = "".join(ch if (ch >= " " and ch != "\x7f") else " " for ch in text)
    # terminal-notifier requires a leading '[' to be escaped.
    stripped = cleaned.lstrip(" ")
    if stripped.startswith("["):
        leading = cleaned[: len(cleaned) - len(stripped)]
        cleaned = leading + "\\[" + stripped[1:]
    return cleaned


def main() -> int:
    notification = json.loads(sys.argv[1])

    if notification.get("type") != "agent-turn-complete":
        return 0

    title = _prepare_notification_text(
        f"Codex: {notification.get('last-assistant-message', 'Turn Complete!')}"
    )
    message = _prepare_notification_text(" ".join(notification.get("input-messages", [])))

    subprocess.check_output(
        [
            "terminal-notifier",
            "-title",
            title,
            "-message",
            message,
            "-group",
            "codex-" + notification.get("thread-id", ""),
            "-sound",
            "Blow",
            "-activate",
            "dev.zed.Zed-Preview",
            "-ignoreDnD",
        ]
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
