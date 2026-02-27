from __future__ import annotations

import re


_BLACKLIST = {
    "easy",
    "normal",
    "veryeasy",
    "extreme",
    "custom",
    "notombstone",
    "keepprogress",
    "disabled",
    "many",
    "few",
    "value",
    "version",
    "progress",
    "progresslevel",
    "playtime",
    "seed",
    "difficulty",
    "settings",
}

_VOWELS = set("aeiouäöüAEIOUÄÖÜ")
_NATURAL_MARKERS = set("()-:,")


def is_blacklisted_exact(value: str) -> bool:
    return value.strip().casefold() in _BLACKLIST


def looks_like_enum_or_camelcase(value: str) -> bool:
    stripped = value.strip()
    if " " in stripped or stripped == "":
        return False
    if not stripped.isalnum():
        return False

    transitions = 0
    for index in range(1, len(stripped)):
        if stripped[index - 1].islower() and stripped[index].isupper():
            transitions += 1

    has_mixed_case = any(char.islower() for char in stripped) and any(char.isupper() for char in stripped)
    return has_mixed_case and transitions >= 1


def looks_like_natural_title(value: str) -> bool:
    stripped = value.strip()
    if len(stripped) < 3 or len(stripped) > 48:
        return False
    if not any(char.isalpha() for char in stripped):
        return False

    has_separator = (
        " " in stripped
        or any(char in "äöüÄÖÜß" for char in stripped)
        or any(char in "()-:," for char in stripped)
    )
    return has_separator


def is_short_gibberish(value: str) -> bool:
    stripped = value.strip()

    if len(stripped) < 3 or len(stripped) > 5:
        return False
    if " " in stripped:
        return False
    if any(char in "äöüÄÖÜ" for char in stripped):
        return False
    if any(char in _NATURAL_MARKERS for char in stripped):
        return False
    if "-" in stripped:
        return False

    has_vowel = any(char in _VOWELS for char in stripped)

    letters = [char for char in stripped if char.isalpha()]
    if letters:
        uppercase_ratio = sum(1 for char in letters if char.isupper()) / len(letters)
    else:
        uppercase_ratio = 0.0

    return (not has_vowel) or (uppercase_ratio >= 0.6)


def is_plausible_world_name(value: str) -> bool:
    stripped = value.strip()
    if len(stripped) < 3 or len(stripped) > 48:
        return False
    if is_short_gibberish(stripped):
        return False
    if is_blacklisted_exact(stripped):
        return False
    if stripped.isdigit():
        return False
    if not any(char.isalpha() for char in stripped):
        return False
    if looks_like_enum_or_camelcase(stripped):
        return False
    if re.fullmatch(r"[A-Za-z0-9_]+", stripped) and len(stripped) <= 4:
        return False
    return True


def score_candidate(value: str) -> float:
    stripped = value.strip()
    if is_blacklisted_exact(stripped):
        return -999.0

    score = 0.0
    if looks_like_natural_title(stripped):
        score += 2.0
    if looks_like_enum_or_camelcase(stripped):
        score -= 2.0
    if " " not in stripped and re.fullmatch(r"[A-Za-z0-9]+", stripped):
        score -= 3.0
    return score
