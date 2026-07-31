"""Option resolution across the two levels, typed access, introspection."""

import pytest

import pathime
from pathime import ChineseVariant, Option, OptionType, Width


def test_engine_value_is_context_default(pinyin):
    with pathime.Context(pinyin) as ctx:
        pinyin.set_option(Option.LATIN_WIDTH, Width.FULL)
        try:
            assert ctx.get_option(Option.LATIN_WIDTH) == Width.FULL
            assert ctx.option_is_set(Option.LATIN_WIDTH) is False
            assert pinyin.option_is_set(Option.LATIN_WIDTH) is True
        finally:
            pinyin.reset_option(Option.LATIN_WIDTH)
        assert ctx.get_option(Option.LATIN_WIDTH) == Width.HALF


def test_context_overrides_engine(pinyin):
    with pathime.Context(pinyin) as ctx:
        ctx.set_option(Option.LATIN_WIDTH, Width.FULL)
        assert ctx.option_is_set(Option.LATIN_WIDTH) is True
        assert pinyin.get_option(Option.LATIN_WIDTH) == Width.HALF
        ctx.reset_option(Option.LATIN_WIDTH)
        assert ctx.get_option(Option.LATIN_WIDTH) == Width.HALF


def test_typed_values_round_trip(pinyin):
    with pathime.Context(pinyin) as ctx:
        assert ctx.get_option(Option.SPECIAL_PHRASES) is True
        variant = ctx.get_option(Option.CHINESE_VARIANT)
        assert isinstance(variant, ChineseVariant)
        fuzzy = ctx.get_option(Option.PINYIN_FUZZY)
        assert isinstance(fuzzy, pathime.PinyinFuzzy)
        ctx.set_option(Option.PINYIN_FUZZY,
                       pathime.PinyinFuzzy.Z_ZH | pathime.PinyinFuzzy.ZH_Z)
        assert ctx.get_option(Option.PINYIN_FUZZY) == (
            pathime.PinyinFuzzy.Z_ZH | pathime.PinyinFuzzy.ZH_Z)
        ctx.reset_option(Option.PINYIN_FUZZY)


def test_pyzy_supports_only_exclusive_variants(pinyin):
    info = pinyin.option_info(Option.CHINESE_VARIANT)
    assert info.valid_values & (1 << ChineseVariant.SIMPLIFIED_ONLY)
    assert info.valid_values & (1 << ChineseVariant.TRADITIONAL_ONLY)
    assert not info.valid_values & (1 << ChineseVariant.ANY)
    with pathime.Context(pinyin) as ctx:
        with pytest.raises(pathime.InvalidArgumentError):
            ctx.set_option(Option.CHINESE_VARIANT, ChineseVariant.ANY)


def test_wrong_setter_type_is_invalid(pinyin):
    with pytest.raises(pathime.InvalidArgumentError):
        pinyin.set_option(Option.LATIN_WIDTH, "full")


def test_int_bounds(pinyin):
    info = pinyin.option_info(Option.MAX_CANDIDATES)
    assert info.type == OptionType.INT
    assert info.min_value == 1
    assert info.default == pathime.DEFAULT_MAX_CANDIDATES
    with pathime.Context(pinyin) as ctx:
        with pytest.raises(pathime.InvalidArgumentError):
            ctx.set_option(Option.MAX_CANDIDATES, 0)


def test_full_inventory_walk(pinyin):
    """The promise a settings UI relies on: every option in
    [0, option_count) describes itself completely."""
    for i in range(pathime.option_count()):
        info = pinyin.option_info(Option(i)) if i <= max(Option) else None
        assert pathime.option_name(i) != ""
        if info is None or not info.supported:
            continue
        if info.type in (OptionType.ENUM, OptionType.FLAGS):
            assert info.valid_values != 0
            for bit in range(64):
                if not info.valid_values & (1 << bit):
                    continue
                value = (1 << bit) if info.type == OptionType.FLAGS else bit
                assert pathime.option_value_name(Option(i), value) != ""


def test_isolated_context_is_passed_by(pinyin):
    changes = []
    with pathime.Context(pinyin,
                         on_composition_changed=changes.append) as ctx:
        ctx.isolate_options()
        # Every implemented option is now an ordinary override here...
        assert ctx.option_is_set(Option.LATIN_WIDTH) is True
        # ...and only those: options this engine does not implement stay unset.
        assert ctx.option_is_set(Option.HANGUL_LAYOUT) is False

        before = len(changes)
        pinyin.set_option(Option.LATIN_WIDTH, Width.FULL)
        try:
            assert ctx.get_option(Option.LATIN_WIDTH) == Width.HALF
            assert len(changes) == before  # the broadcast skipped this context
        finally:
            pinyin.reset_option(Option.LATIN_WIDTH)

        # reset_option drops one copy and re-attaches that option.
        ctx.reset_option(Option.LATIN_WIDTH)
        pinyin.set_option(Option.LATIN_WIDTH, Width.FULL)
        try:
            assert ctx.get_option(Option.LATIN_WIDTH) == Width.FULL
        finally:
            pinyin.reset_option(Option.LATIN_WIDTH)


def test_isolate_at_construction_reads_engine_as_template(pinyin):
    pinyin.set_option(Option.CHINESE_VARIANT, ChineseVariant.TRADITIONAL_ONLY)
    try:
        with pathime.Context(pinyin, isolate=True) as ctx:
            pinyin.reset_option(Option.CHINESE_VARIANT)
            assert (ctx.get_option(Option.CHINESE_VARIANT)
                    == ChineseVariant.TRADITIONAL_ONLY)
            assert ctx.option_is_set(Option.CHINESE_VARIANT) is True
    finally:
        pinyin.reset_option(Option.CHINESE_VARIANT)


def test_engine_set_updates_open_context_immediately(pinyin):
    changes = []
    with pathime.Context(pinyin,
                         on_composition_changed=changes.append) as ctx:
        ctx.type("ma")
        assert "马" in ctx.composition.candidates
        before = len(changes)
        pinyin.set_option(Option.CHINESE_VARIANT,
                          ChineseVariant.TRADITIONAL_ONLY)
        try:
            assert len(changes) > before  # announced, not silent
            assert "馬" in ctx.composition.candidates
            assert "马" not in ctx.composition.candidates
        finally:
            pinyin.reset_option(Option.CHINESE_VARIANT)
