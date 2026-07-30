"""Table engine: table selection by option, legends, tier-3 defaults."""

import pytest

import pathime
from pathime import Key, Option


@pytest.fixture(scope="module")
def cangjie(table):
    table.set_option(Option.TABLE_FILE, "cangjie5")
    yield table
    table.reset_option(Option.TABLE_FILE)


def test_installed_tables_are_enumerable(table):
    info = table.option_info(Option.TABLE_FILE)
    names = [pathime.option_value_name(Option.TABLE_FILE, i)
             for i in range(info.valid_value_count)]
    assert "cangjie5" in names


def test_no_table_handles_nothing(table):
    with pathime.Context(table) as ctx:
        ctx.set_option(Option.TABLE_FILE, "")
        assert ctx.get_option(Option.TABLE_FILE) == ""
        assert ctx.process_key("a") is False


def test_bad_table_is_backend_error_and_keeps_previous(cangjie):
    with pathime.Context(cangjie) as ctx:
        with pytest.raises(pathime.BackendError):
            ctx.set_option(Option.TABLE_FILE, "no-such-table")
        assert ctx.get_option(Option.TABLE_FILE) == "cangjie5"


def test_preedit_shows_key_legends(cangjie):
    with pathime.Context(cangjie) as ctx:
        ctx.type("a")
        assert ctx.composition.preedit == "日"  # cangjie legend for 'a'
        assert "日" in ctx.composition.candidates


def test_return_commits_the_letters(cangjie):
    with pathime.Context(cangjie) as ctx:
        ctx.type("a")
        ctx.process_key(Key.RETURN)
        assert ctx.take_committed() == "a"


def test_select_commits_the_character(cangjie):
    with pathime.Context(cangjie) as ctx:
        ctx.type("a")
        index = ctx.composition.candidates.index("日")
        ctx.select_candidate(index)
        assert ctx.take_committed() == "日"


def test_table_declares_wildcard(cangjie):
    with pathime.Context(cangjie) as ctx:
        # A compiled table is given a single wildcard where its alphabet
        # leaves room; the value is a tier-3 declaration, not a library
        # default (the library default is empty).
        info = ctx.option_info(Option.TABLE_SINGLE_WILDCARD)
        assert info.default == ""
        assert ctx.get_option(Option.TABLE_SINGLE_WILDCARD) != ""
