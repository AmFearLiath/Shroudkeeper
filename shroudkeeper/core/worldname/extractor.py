from __future__ import annotations

import math
from pathlib import Path

from core.worldname.scoring import is_plausible_world_name, score_candidate
from core.worldname.strings import (
    dedupe_case_insensitive,
    extract_ascii_strings,
    extract_utf8_strings,
    sanitize_string,
)
from core.worldname.zstd_scan import find_magic_offsets, try_decompress_from_offset


def extract_world_name_from_info_file(
    path: Path,
    max_output_size: int = 8 * 1024 * 1024,
    top_n: int = 5,
) -> tuple[str | None, list[str]]:
    try:
        raw = path.read_bytes()
    except Exception:
        return None, []

    offsets = find_magic_offsets(raw)
    if not offsets:
        return None, []

    all_candidates: list[str] = []

    for offset in offsets:
        payload = try_decompress_from_offset(raw, offset, max_output_size)
        if payload is None:
            continue

        ascii_values = extract_ascii_strings(payload, min_len=4)
        utf8_values = extract_utf8_strings(payload, min_len=4)
        combined = ascii_values + utf8_values

        for value in combined:
            cleaned = sanitize_string(value)
            if cleaned:
                all_candidates.append(cleaned)

    occurrences_by_key: dict[str, int] = {}
    for value in all_candidates:
        key = value.casefold()
        occurrences_by_key[key] = occurrences_by_key.get(key, 0) + 1

    unique_candidates = dedupe_case_insensitive(all_candidates)
    plausible = [value for value in unique_candidates if is_plausible_world_name(value)]

    scored = sorted(
        (
            (
                value,
                score_candidate(value)
                + min(2.0, math.log2(occurrences_by_key.get(value.casefold(), 1) + 1) * 0.5),
            )
            for value in plausible
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    if not scored:
        return None, []

    top = [value for value, _score in scored[: max(1, top_n)]]
    best_guess = top[0] if top else None
    return best_guess, top
