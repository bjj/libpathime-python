"""Session setup: locate the library, initialize once, share engines.

The library is named by PATHIME_LIBRARY; without it, the conventional local
build (/tmp/pathime-install) is tried so a plain `pytest` works after the
build steps in CLAUDE.md. The library is initialized once per session with a
throwaway data directory — pathime_init() is process-global and engines learn
from what tests select, so isolation comes from the fresh directory, not from
re-initializing between tests.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

_DEFAULT_LIBRARY = "/tmp/pathime-install/lib/libpathime.so"

if "PATHIME_LIBRARY" not in os.environ and os.path.exists(_DEFAULT_LIBRARY):
    os.environ["PATHIME_LIBRARY"] = _DEFAULT_LIBRARY

import pathime  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def library(tmp_path_factory):
    pathime.init(data_dir=str(tmp_path_factory.mktemp("pathime-userdata")))
    yield
    # No shutdown: session fixtures with engines still open would have to be
    # torn down first, and the process is exiting anyway.


def _engine(engine_id):
    if not pathime.has_engine(engine_id):
        pytest.skip(f"{engine_id.name} engine not available in this build")
    eng = pathime.Engine(engine_id)
    yield eng
    eng.close()


@pytest.fixture(scope="module")
def hangul(library):
    yield from _engine(pathime.EngineId.HANGUL)


@pytest.fixture(scope="module")
def anthy(library):
    yield from _engine(pathime.EngineId.ANTHY)


@pytest.fixture(scope="module")
def pinyin(library):
    yield from _engine(pathime.EngineId.PINYIN)


@pytest.fixture(scope="module")
def bopomofo(library):
    yield from _engine(pathime.EngineId.BOPOMOFO)


@pytest.fixture(scope="module")
def table(library):
    yield from _engine(pathime.EngineId.TABLE)
