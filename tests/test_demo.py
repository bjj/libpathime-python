"""Drive the demo's UI-free model headlessly: the phone in prose."""

import os
import sys

import pytest

import pathime
from pathime import EngineId, Key

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "demo"))

from phone_keyboard import STRIP_SIZE, PhoneKeyboard  # noqa: E402


@pytest.fixture
def phone(library):
    ids = [e for e in EngineId if pathime.has_engine(e)]
    if not ids:
        pytest.skip("no engines available")
    p = PhoneKeyboard(ids)
    yield p
    p.close()


def _activate(phone, engine_id):
    if engine_id not in phone.contexts:
        pytest.skip(f"{engine_id.name} not available")
    while phone.active != engine_id:
        phone.switch_engine()


def test_type_and_tap_candidate(phone):
    _activate(phone, EngineId.PINYIN)
    for ch in "nihao":
        phone.key(ch)
    strip, highlight = phone.strip()
    assert strip[0] == "你好"
    assert highlight == 0
    phone.tap_candidate(1)
    assert phone.text == "你好"
    assert phone.composition.preedit == ""


def test_unhandled_keys_fall_through_to_document(phone):
    _activate(phone, EngineId.HANGUL)
    for ch in "gks":
        phone.key(ch)
    phone.key(Key.SPACE)  # hangul declines space; the document gets it
    assert phone.text == "한 "


def test_paging_grows_the_list(phone):
    _activate(phone, EngineId.PINYIN)
    # Start with a capped list, the case where more may exist behind it.
    phone.context.set_option(pathime.Option.MAX_CANDIDATES, STRIP_SIZE)
    phone.key("m")
    phone.key("a")
    assert phone.composition.candidate_count == STRIP_SIZE
    phone.page_strip(+1)
    assert phone.composition.candidate_count > STRIP_SIZE
    assert phone.page == 1
    # "ma" is finite: paging to the very end must stop asking for more once
    # the count falls below the cap.
    for _ in range(20):
        phone.page_strip(+1)
    total = phone.composition.candidate_count
    assert total < phone.context.get_option(pathime.Option.MAX_CANDIDATES)
    phone.reset()
    phone.context.reset_option(pathime.Option.MAX_CANDIDATES)


def test_engine_switch_keeps_composition(phone):
    if len(phone.contexts) < 2:
        pytest.skip("needs two engines")
    _activate(phone, EngineId.PINYIN)
    phone.key("n")
    phone.key("i")
    phone.switch_engine()
    phone.switch_engine()  # not necessarily back yet; go all the way round
    while phone.active != EngineId.PINYIN:
        phone.switch_engine()
    assert phone.composition.preedit == "ni"
    phone.reset()


def test_surrounding_text_follows_document(phone):
    _activate(phone, EngineId.PINYIN)
    phone.key("1")  # pinyin handles digits (latin width); document gets "1"
    phone.key(".")
    assert phone.text == "1."  # decimal point survived the look-behind
