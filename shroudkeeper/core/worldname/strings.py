from __future__ import annotations

import re


_ASCII_PATTERN = re.compile(rb"[\x20-\x7E]{4,}")


def extract_ascii_strings(payload: bytes, min_len: int = 4) -> list[str]:
    pattern = re.compile(rb"[\x20-\x7E]{" + str(min_len).encode("ascii") + rb",}")
    results: list[str] = []
    for match in pattern.finditer(payload):
        try:
            value = match.group(0).decode("ascii", errors="ignore")
        except Exception:
            continue
        if value:
            results.append(value)
    return results


def extract_utf8_strings(payload: bytes, min_len: int = 4) -> list[str]:
    text = payload.decode("utf-8", errors="ignore")
    current: list[str] = []
    results: list[str] = []

    for char in text:
        if char.isprintable() and char not in {"\x00", "\x0b", "\x0c"}:
            current.append(char)
            continue

        if len(current) >= min_len:
            results.append("".join(current))
        current = []

    if len(current) >= min_len:
        results.append("".join(current))

    return results


def sanitize_string(value: str) -> str:
    text = value.replace("\x00", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def dedupe_case_insensitive(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(value)
    return deduped
