"""Pinyin end to end: the README example, candidates, cursor, commits."""

import pytest

import pathime
from pathime import Key, Option


@pytest.fixture
def ctx(pinyin):
    with pathime.Context(pinyin) as c:
        yield c


def test_nihao_first_candidate(ctx):
    ctx.type("nihao")
    comp = ctx.composition
    assert comp.preedit == "ni hao"
    assert comp.candidates[0] == "你好"
    ctx.select_candidate(0)
    assert ctx.take_committed() == "你好"
    assert ctx.composition.preedit == ""


def test_printable_keys_are_handled(ctx):
    assert ctx.process_key("n") is True


def test_return_commits_as_typed(ctx):
    ctx.type("nihao")
    handled = ctx.process_key(Key.RETURN)
    assert handled is True
    # Separators between syllables are a commit-time normalization.
    assert ctx.take_committed() == "nihao"


def test_greedy_selection_produces_fresh_list(ctx):
    ctx.type("nihao")
    # Select just 你 — the remaining "hao" gets a fresh list.
    index = ctx.composition.candidates.index("你")
    ctx.select_candidate(index)
    comp = ctx.composition
    assert comp.preedit.startswith("你")
    assert comp.preedit_settled == 1
    assert comp.candidates  # alternatives for "hao"
    assert ctx.committed == ""  # nothing committed yet


def test_candidate_by_index_matches_snapshot(ctx):
    ctx.type("ma")
    comp = ctx.composition
    for i, text in enumerate(comp.candidates[:10]):
        assert ctx.candidate(i) == text


def test_candidate_cursor_roundtrip(ctx):
    ctx.type("ma")
    ctx.set_candidate_cursor(2)
    assert ctx.composition.candidate_cursor == 2
    with pytest.raises(pathime.InvalidArgumentError):
        ctx.set_candidate_cursor(len(ctx.composition.candidates))


def test_incomplete_input_reaches_longer_entries(ctx):
    assert ctx.get_option(Option.INCOMPLETE_INPUT) is True
    ctx.type("nh")
    assert "你好" in ctx.composition.candidates


def test_backspace_shrinks_preedit(ctx):
    ctx.type("nihao")
    ctx.process_key(Key.BACKSPACE)
    assert ctx.composition.preedit == "ni ha"


def test_escape_abandons_composition(ctx):
    ctx.type("nihao")
    ctx.process_key(Key.ESCAPE)
    assert ctx.composition.preedit == ""
    assert ctx.committed == ""


def test_explicit_commit_keeps_text(ctx):
    ctx.type("nihao")
    ctx.commit()
    assert ctx.take_committed() == "nihao"
    # Empty composition: commit is a documented no-op.
    ctx.commit()
    assert ctx.take_committed() == ""


def test_reset_discards_silently(ctx):
    ctx.type("nihao")
    ctx.reset()
    assert ctx.composition.preedit == ""
    assert ctx.committed == ""


def test_max_candidates_caps_and_appends(ctx):
    ctx.set_option(Option.MAX_CANDIDATES, 5)
    ctx.type("ma")
    first = ctx.composition.candidates
    assert len(first) == 5
    ctx.set_option(Option.MAX_CANDIDATES, 10)
    more = ctx.composition.candidates
    assert len(more) > 5
    assert more[:5] == first  # appended, never renumbered


def test_full_stop_after_digit_stays_period(ctx):
    ctx.set_surrounding_text("1", 1)
    ctx.process_key(".")
    assert ctx.take_committed() == "."
    ctx.set_surrounding_text("abc", 3)
    ctx.process_key(".")
    assert ctx.take_committed() == "。"
