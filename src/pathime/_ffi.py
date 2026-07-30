"""ctypes layer: a transcription of pathime.h, kept in its order.

Nothing here is public. The structs, prototypes and helpers mirror the header
one to one; everything Pythonic lives in ``pathime/__init__.py``.

Library loading order:

1. ``PATHIME_LIBRARY`` — full path to the shared library. The build tree and
   test runs use this.
2. ``ctypes.util.find_library("pathime")`` — an installed library on the
   system loader's path.
3. The platform's bare name (``libpathime.so.0`` / ``libpathime.so`` on Linux,
   ``pathime.dll`` on Windows, ``libpathime.dylib`` on macOS), for a library
   sitting on the loader path without ldconfig knowledge.

On Windows the DLL's dependencies (the vendored backend DLLs) must be findable
too; pass the directory holding them through ``os.add_dll_directory`` before
importing, or set ``PATHIME_LIBRARY`` and the binding adds its directory.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import sys
from ctypes import (
    CFUNCTYPE,
    POINTER,
    c_bool,
    c_char_p,
    c_int,
    c_int64,
    c_size_t,
    c_ssize_t,
    c_uint32,
    c_uint64,
    c_void_p,
)


# =========================================================================
# Structs
# =========================================================================

class pathime_str_t(ctypes.Structure):
    _fields_ = [
        ("bytes", c_void_p),  # const char *; c_void_p so len-delimited reads
        ("len", c_size_t),    # are explicit and NULs are preserved
    ]

    def to_str(self) -> str:
        if not self.bytes or self.len == 0:
            return ""
        return ctypes.string_at(self.bytes, self.len).decode("utf-8")


class pathime_init_params_t(ctypes.Structure):
    _fields_ = [
        ("struct_size", c_size_t),
        ("data_dir", c_char_p),
        ("resource_dir", c_char_p),
    ]


class pathime_key_event_t(ctypes.Structure):
    _fields_ = [
        ("struct_size", c_size_t),
        ("keysym", c_uint32),
        ("layout_key", c_uint32),
        ("modifiers", c_uint32),
    ]


class pathime_composition_t(ctypes.Structure):
    _fields_ = [
        ("struct_size", c_size_t),
        ("preedit", pathime_str_t),
        ("preedit_settled", c_size_t),
        ("candidate_count", c_size_t),
        ("candidate_cursor", c_size_t),
    ]


COMMIT_TEXT_FN = CFUNCTYPE(None, c_void_p, pathime_str_t)
DELETE_SURROUNDING_FN = CFUNCTYPE(None, c_void_p, c_ssize_t, c_size_t)
COMPOSITION_CHANGED_FN = CFUNCTYPE(None, c_void_p, POINTER(pathime_composition_t))


class pathime_client_t(ctypes.Structure):
    _fields_ = [
        ("struct_size", c_size_t),
        ("commit_text", COMMIT_TEXT_FN),
        ("delete_surrounding_text", DELETE_SURROUNDING_FN),
        ("composition_changed", COMPOSITION_CHANGED_FN),
    ]


class pathime_option_info_t(ctypes.Structure):
    _fields_ = [
        ("struct_size", c_size_t),
        ("type", c_int),
        ("supported", c_bool),
        ("resets_composition", c_bool),
        ("default_value", c_int64),
        ("min_value", c_int64),
        ("max_value", c_int64),
        ("valid_values", c_uint64),
        ("default_string", pathime_str_t),
        ("valid_value_count", c_size_t),
    ]


# =========================================================================
# Library loading
# =========================================================================

def _candidate_names() -> list[str]:
    if sys.platform == "win32":
        return ["pathime.dll"]
    if sys.platform == "darwin":
        return ["libpathime.0.dylib", "libpathime.dylib"]
    return ["libpathime.so.0", "libpathime.so"]


def load_library(path: str | None = None) -> ctypes.CDLL:
    """Load libpathime and attach every prototype. Raises OSError on failure."""
    tried: list[str] = []
    lib = None

    explicit = path or os.environ.get("PATHIME_LIBRARY")
    if explicit:
        if sys.platform == "win32":
            # The vendored backend DLLs sit beside pathime.dll; make sure the
            # loader can see them.
            os.add_dll_directory(os.path.dirname(os.path.abspath(explicit)))
        lib = ctypes.CDLL(explicit)
    else:
        found = ctypes.util.find_library("pathime")
        names = [found] if found else []
        names += _candidate_names()
        for name in names:
            try:
                lib = ctypes.CDLL(name)
                break
            except OSError:
                tried.append(name)
        if lib is None:
            raise OSError(
                "cannot load libpathime (tried: %s); set PATHIME_LIBRARY to "
                "the full path of the shared library" % ", ".join(tried)
            )

    _declare(lib)
    return lib


def _declare(lib: ctypes.CDLL) -> None:
    """Set argtypes/restype for every function, in the header's order."""

    def fn(name, restype, *argtypes):
        f = getattr(lib, name)
        f.restype = restype
        f.argtypes = list(argtypes)

    status = c_int
    engine_p = c_void_p
    ctx_p = c_void_p

    # Version
    fn("pathime_version", c_uint32)
    fn("pathime_version_string", c_char_p)

    # Status
    fn("pathime_status_string", c_char_p, c_int)

    # Library lifetime
    fn("pathime_init", status, POINTER(pathime_init_params_t))
    fn("pathime_shutdown", None)

    # Engine
    fn("pathime_has_engine", c_bool, c_int)
    fn("pathime_engine_create", status, c_int, POINTER(engine_p))
    fn("pathime_engine_destroy", None, engine_p)
    fn("pathime_engine_id", c_int, engine_p)
    fn("pathime_engine_requirements", c_uint32, engine_p)

    # Input context
    fn("pathime_context_create", status, engine_p,
       POINTER(pathime_client_t), c_void_p, POINTER(ctx_p))
    fn("pathime_context_destroy", None, ctx_p)
    fn("pathime_context_engine", engine_p, ctx_p)
    fn("pathime_context_user_data", c_void_p, ctx_p)
    fn("pathime_context_requirements", c_uint32, ctx_p)
    fn("pathime_context_process_key", status, ctx_p,
       POINTER(pathime_key_event_t), POINTER(c_bool))
    fn("pathime_context_composition", POINTER(pathime_composition_t), ctx_p)
    fn("pathime_context_candidate", status, ctx_p, c_size_t,
       POINTER(pathime_str_t))
    fn("pathime_context_set_candidate_cursor", status, ctx_p, c_size_t)
    fn("pathime_context_select_candidate", status, ctx_p, c_size_t)
    fn("pathime_context_set_surrounding_text", status, ctx_p, pathime_str_t,
       c_size_t)
    fn("pathime_context_commit", status, ctx_p)
    fn("pathime_context_reset", status, ctx_p)

    # Options
    fn("pathime_option_count", c_size_t)
    fn("pathime_option_name", c_char_p, c_int)
    fn("pathime_option_value_name", c_char_p, c_int, c_int64)
    fn("pathime_engine_option_info", status, engine_p, c_int,
       POINTER(pathime_option_info_t))

    fn("pathime_engine_set_option_bool", status, engine_p, c_int, c_bool)
    fn("pathime_engine_set_option_int", status, engine_p, c_int, c_int64)
    fn("pathime_engine_set_option_string", status, engine_p, c_int, c_char_p)
    fn("pathime_context_set_option_bool", status, ctx_p, c_int, c_bool)
    fn("pathime_context_set_option_int", status, ctx_p, c_int, c_int64)
    fn("pathime_context_set_option_string", status, ctx_p, c_int, c_char_p)
    fn("pathime_engine_reset_option", status, engine_p, c_int)
    fn("pathime_context_reset_option", status, ctx_p, c_int)

    fn("pathime_engine_get_option_bool", status, engine_p, c_int,
       POINTER(c_bool))
    fn("pathime_engine_get_option_int", status, engine_p, c_int,
       POINTER(c_int64))
    fn("pathime_engine_get_option_string", status, engine_p, c_int,
       POINTER(pathime_str_t))
    fn("pathime_context_get_option_bool", status, ctx_p, c_int,
       POINTER(c_bool))
    fn("pathime_context_get_option_int", status, ctx_p, c_int,
       POINTER(c_int64))
    fn("pathime_context_get_option_string", status, ctx_p, c_int,
       POINTER(pathime_str_t))
    fn("pathime_engine_option_is_set", c_bool, engine_p, c_int)
    fn("pathime_context_option_is_set", c_bool, ctx_p, c_int)


def make_str(text: bytes) -> pathime_str_t:
    """Build a pathime_str_t borrowing ``text``.

    The caller must keep ``text`` alive across the call it is passed to; every
    use in this binding passes it straight into a synchronous function.
    """
    buf = ctypes.cast(c_char_p(text), c_void_p)
    return pathime_str_t(buf, len(text))
