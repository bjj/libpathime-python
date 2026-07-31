"""Behaviour the binding itself adds: copies, callbacks, units, keysyms."""

import pytest

import pathime
from pathime import Key, KeyEvent, Mod, Option


def test_keysym_for_char_follows_x11_rule():
    assert pathime.keysym_for_char("a") == 0x61
    assert pathime.keysym_for_char("é") == 0xE9  # below U+0100: the scalar
    assert pathime.keysym_for_char("中") == 0x01000000 + 0x4E2D


def test_engine_enum_matches_library_names():
    # The check pathime_engine_name exists for: a transposed enum value would
    # pass every structural check and create the wrong engine.
    for engine_id in pathime.EngineId:
        assert pathime.engine_name(engine_id) == engine_id.name.lower()
    assert pathime.engine_name(99) == ""


def test_key_event_accepts_characters():
    event = KeyEvent("Q", layout_key="q", modifiers=Mod.SHIFT)._to_c()
    assert event.keysym == ord("Q")
    assert event.layout_key == ord("q")
    assert event.modifiers == Mod.SHIFT


def test_snapshots_are_independent(pinyin):
    with pathime.Context(pinyin) as ctx:
        ctx.type("nihao")
        before = ctx.composition
        candidates = before.candidates
        ctx.select_candidate(0)
        # The snapshot taken before the mutating call is untouched by it.
        assert before.preedit == "ni hao"
        assert before.candidates == candidates
        assert ctx.composition is not before


def test_commit_callback_replaces_buffer(pinyin):
    committed = []
    with pathime.Context(pinyin, on_commit=committed.append) as ctx:
        ctx.type("nihao")
        ctx.select_candidate(0)
        assert committed == ["你好"]
        assert ctx.committed == ""  # buffer unused when a callback is given


def test_composition_changed_sees_current_snapshot(pinyin):
    seen = []
    with pathime.Context(
            pinyin, on_composition_changed=lambda c: seen.append(c)) as ctx:
        ctx.type("ni")
        assert seen[-1] is ctx.composition
        assert seen[-1].candidates  # candidates readable inside the callback


def test_callback_exception_is_deferred_not_lost(pinyin):
    class Boom(RuntimeError):
        pass

    def explode(comp):
        raise Boom("client bug")

    with pathime.Context(pinyin, on_composition_changed=explode) as ctx:
        with pytest.raises(Boom):
            ctx.process_key("n")
        # The library completed its dispatch; the context is still usable.
        ctx._on_composition_changed = None
        ctx.process_key("i")
        assert ctx.composition.preedit == "ni"


def test_surrounding_text_positions_are_str_indices(pinyin):
    with pathime.Context(pinyin) as ctx:
        # 𝄞 is outside the BMP: one scalar value, one Python index — and
        # the binding must not let UTF-16 habits (or byte offsets) creep in.
        text = "𝄞x1"
        ctx.set_surrounding_text(text, 3)  # cursor after the digit
        ctx.process_key(".")
        assert ctx.take_committed() == "."  # digit look-behind saw "1"
        with pytest.raises(pathime.InvalidArgumentError):
            ctx.set_surrounding_text(text, 4)


def test_embedded_nul_is_rejected(pinyin):
    with pathime.Context(pinyin) as ctx:
        with pytest.raises(pathime.InvalidArgumentError):
            ctx.set_surrounding_text("a\x00b", 0)


def test_close_is_idempotent_and_ordered(library):
    engine = pathime.Engine(pathime.EngineId.PINYIN)
    ctx = pathime.Context(engine)
    ctx.close()
    ctx.close()
    engine.close()
    engine.close()


def test_string_option_round_trip(table):
    with pathime.Context(table) as ctx:
        ctx.set_option(Option.TABLE_FILE, "cangjie5")
        value = ctx.get_option(Option.TABLE_FILE)
        assert value == "cangjie5"
        assert isinstance(value, str)
        ctx.set_option(Option.TABLE_FILE, "")


def test_modifier_chord_is_declined(pinyin):
    with pathime.Context(pinyin) as ctx:
        assert ctx.process_key(KeyEvent("c", modifiers=Mod.CONTROL)) is False
        assert ctx.composition.preedit == ""
