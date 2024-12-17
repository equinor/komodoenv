import re


def green(text: str) -> str:
    return f"\x1b[32m{text}\x1b[0m"


def blue(text: str) -> str:
    return f"\x1b[34m{text}\x1b[0m"


def yellow(text: str) -> str:
    return f"\x1b[33m{text}\x1b[0m"


def strip_color(text: str) -> str:
    ansi_escape = re.compile(r"(?:\x1b\[[0-9;]*m)")
    return ansi_escape.sub("", text)
