"""Library lifetime, version, engine availability, error mapping."""

import re

import pytest

import pathime


def test_version_string_matches_number():
    text = pathime.version()
    assert re.fullmatch(r"\d+\.\d+\.\d+", text)
    major, minor, patch = (int(x) for x in text.split("."))
    assert pathime.version_number() == major * 1000000 + minor * 1000 + patch


def test_init_twice_is_already_initialized(library):
    with pytest.raises(pathime.AlreadyInitializedError):
        pathime.init()


def test_has_engine_rejects_nonsense(library):
    assert pathime.has_engine(999) is False


def test_engine_identity(pinyin):
    assert pinyin.id == pathime.EngineId.PINYIN


def test_unknown_engine_error(library):
    if pathime.has_engine(pathime.EngineId.HANGUL):
        pytest.skip("needs a build without hangul")
    with pytest.raises(pathime.UnknownEngineError):
        pathime.Engine(pathime.EngineId.HANGUL)


def test_option_inventory_is_dense(library):
    count = pathime.option_count()
    assert count >= 31  # every option the bound header names
    names = [pathime.option_name(i) for i in range(count)]
    assert all(names), "dense ids promise a name for every option"
    assert len(set(names)) == count
    assert pathime.option_name(count) == ""


def test_binding_option_enum_matches_library(library):
    # The binding transcribes the option enum by hand; the stable names
    # catch a transcription slip.
    assert pathime.option_name(pathime.Option.CHINESE_VARIANT) == "chinese-variant"
    assert pathime.option_name(pathime.Option.TABLE_FILE) == "table-file"


def test_option_value_names(library):
    name = pathime.option_value_name(
        pathime.Option.CHINESE_VARIANT, pathime.ChineseVariant.TRADITIONAL_FIRST)
    assert name == "traditional-first"
    # BOOL options name no values.
    assert pathime.option_value_name(pathime.Option.LEARNING, 1) == ""
