"""Anthy: romaji preedit, conversion, prediction, kana script."""

import pytest

import pathime
from pathime import AnthyScript, Key, Option


@pytest.fixture
def ctx(anthy):
    with pathime.Context(anthy) as c:
        yield c


def test_romaji_becomes_kana_preedit(ctx):
    ctx.type("nihongo")
    assert ctx.composition.preedit == "にほんご"


def test_prediction_offers_candidates_before_convert(ctx):
    assert ctx.get_option(Option.PREDICTION) is True
    ctx.type("nihongo")
    assert "日本語" in ctx.composition.candidates
    # Browsing before conversion leaves the preedit alone.
    ctx.set_candidate_cursor(1)
    assert ctx.composition.preedit == "にほんご"


def test_space_converts_and_previews(ctx):
    ctx.type("nihongo")
    ctx.process_key(Key.SPACE)
    assert ctx.composition.preedit == "日本語"
    ctx.process_key(Key.RETURN)
    assert ctx.take_committed() == "日本語"


def test_return_commits_kana_as_typed(ctx):
    ctx.type("nihongo")
    ctx.process_key(Key.RETURN)
    assert ctx.take_committed() == "にほんご"


def test_trailing_n_normalizes_at_commit(ctx):
    ctx.type("hon")
    assert ctx.composition.preedit == "ほn"  # one more key still decides
    ctx.process_key(Key.RETURN)
    assert ctx.take_committed() == "ほん"


def test_katakana_script(ctx):
    ctx.set_option(Option.ANTHY_KANA_SCRIPT, AnthyScript.KATAKANA)
    ctx.type("nihongo")
    assert ctx.composition.preedit == "ニホンゴ"


def test_typing_method_resets_composition(anthy):
    info = anthy.option_info(Option.ANTHY_TYPING_METHOD)
    assert info.resets_composition is True
    with pathime.Context(anthy) as ctx:
        ctx.type("nihon")
        ctx.set_option(Option.ANTHY_TYPING_METHOD, pathime.AnthyTyping.KANA)
        assert ctx.composition.preedit == ""
