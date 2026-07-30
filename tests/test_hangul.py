"""Hangul: syllable composition, requirements, the preedit-none client."""

import pytest

import pathime
from pathime import HangulPreedit, Key, Option, Requires


@pytest.fixture
def ctx(hangul):
    with pathime.Context(hangul) as c:
        yield c


def test_syllable_composition(ctx):
    ctx.type("gks")  # ㅎ ㅏ ㄴ on 2-set
    assert ctx.composition.preedit == "한"
    ctx.commit()
    assert ctx.take_committed() == "한"


def test_syllable_commits_when_next_begins(ctx):
    ctx.type("gksrmf")  # 한글
    assert ctx.take_committed() == "한"
    assert ctx.composition.preedit == "글"


def test_no_candidates(ctx):
    ctx.type("gks")
    assert ctx.composition.candidates == ()
    with pytest.raises(pathime.InvalidArgumentError):
        ctx.select_candidate(0)


def test_backspace_removes_one_jamo(ctx):
    ctx.type("gks")
    ctx.process_key(Key.BACKSPACE)
    assert ctx.composition.preedit == "하"


def test_max_candidates_unsupported(hangul):
    info = hangul.option_info(Option.MAX_CANDIDATES)
    assert info.supported is False
    with pytest.raises(pathime.UnsupportedError):
        hangul.set_option(Option.MAX_CANDIDATES, 10)


def test_word_preedit_accumulates(hangul):
    with pathime.Context(hangul) as ctx:
        ctx.set_option(Option.HANGUL_PREEDIT, HangulPreedit.WORD)
        ctx.type("gksrmf")
        comp = ctx.composition
        assert comp.preedit == "한글"
        assert comp.preedit_settled == 1  # 한 is done, 글 still open
        assert ctx.committed == ""
        ctx.process_key(Key.SPACE)  # word boundary; hangul declines space
        assert ctx.take_committed() == "한글"


def test_preedit_none_requires_delete_callback(hangul):
    engine_default = hangul.requirements
    assert engine_default == Requires(0)
    with pathime.Context(hangul) as ctx:
        with pytest.raises(pathime.MissingCallbackError):
            ctx.set_option(Option.HANGUL_PREEDIT, HangulPreedit.NONE)


def test_preedit_none_builds_syllable_in_document(hangul):
    """The mode that exists for clients without a preedit: each keystroke
    commits, and the syllable grows by delete-and-recommit."""
    doc = []  # the client's document, one scalar value per entry
    cursor = [0]

    def on_commit(text):
        for ch in text:
            doc.insert(cursor[0], ch)
            cursor[0] += 1

    def on_delete(offset, count):
        start = cursor[0] + offset
        del doc[start:start + count]
        cursor[0] = start

    with pathime.Context(hangul, on_commit=on_commit,
                         on_delete_surrounding=on_delete) as ctx:
        ctx.set_option(Option.HANGUL_PREEDIT, HangulPreedit.NONE)
        assert ctx.requirements == (Requires.SURROUNDING_TEXT
                                    | Requires.DELETE_SURROUNDING)
        for key in "gks":
            ctx.set_surrounding_text("".join(doc), cursor[0])
            ctx.process_key(key)
        assert "".join(doc) == "한"
        assert ctx.composition.preedit == ""


def test_engine_level_none_caps_for_incapable_context(hangul):
    """An engine-level set succeeds; a context whose client lacks the
    callback resolves to SYLLABLE instead, visibly."""
    with pathime.Context(hangul) as ctx:  # no delete callback
        hangul.set_option(Option.HANGUL_PREEDIT, HangulPreedit.NONE)
        try:
            assert hangul.get_option(Option.HANGUL_PREEDIT) == HangulPreedit.NONE
            assert ctx.get_option(Option.HANGUL_PREEDIT) == HangulPreedit.SYLLABLE
        finally:
            hangul.reset_option(Option.HANGUL_PREEDIT)
