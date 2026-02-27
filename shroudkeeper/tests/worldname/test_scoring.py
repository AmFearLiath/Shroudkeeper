from __future__ import annotations

from core.worldname.scoring import is_plausible_world_name


def test_blacklist_easy_rejected() -> None:
    assert is_plausible_world_name("Easy") is False


def test_natural_name_accepted() -> None:
    assert is_plausible_world_name("Meine Welt (Solo)") is True


def test_camelcase_rejected() -> None:
    assert is_plausible_world_name("NoTombstone") is False


def test_short_gibberish_rejected() -> None:
    assert is_plausible_world_name("yMH") is False


def test_testwelt_accepted() -> None:
    assert is_plausible_world_name("Testwelt") is True
