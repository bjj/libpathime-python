"""Python binding for libpathime — a CJK input method engine library.

The C API is one header, ``pathime.h``; this package wraps it in a Pythonic
surface:

- :func:`init` / :func:`shutdown` — library lifetime.
- :class:`Engine` — one input method plus shared state; a context manager.
- :class:`Context` — one client destination; a context manager. Callbacks are
  constructor arguments; committed text also accumulates on the context for
  callers that prefer polling.
- Enums mirror the C ones (:class:`EngineId`, :class:`Option`, :class:`Key`,
  :class:`Mod`, value enums per option); errors are exceptions mirroring
  ``pathime_status_t``.

Everything the library returns is copied into Python objects at the boundary,
so nothing here borrows C memory. Positions and counts are in Unicode scalar
values, which is exactly Python ``str`` indexing; only byte lengths exist and
they never surface here.

The C library is synchronous, starts no threads, and requires that calls into
it never overlap. The binding adds no locking; a multi-threaded client must
serialize its own calls (a single input thread is the expected arrangement).
"""

from __future__ import annotations

import ctypes
import enum
import weakref
from dataclasses import dataclass

from . import _ffi

__all__ = [
    "AlreadyInitializedError",
    "BackendError",
    "ChineseVariant",
    "Composition",
    "Context",
    "Engine",
    "EngineId",
    "Error",
    "InvalidArgumentError",
    "Key",
    "KeyEvent",
    "Mod",
    "MissingCallbackError",
    "NotInitializedError",
    "Option",
    "OptionInfo",
    "OptionType",
    "OutOfMemoryError",
    "Requires",
    "UnknownEngineError",
    "UnsupportedError",
    "AnthyOnPeriod",
    "AnthyPeriod",
    "AnthyScript",
    "AnthySymbol",
    "AnthyTyping",
    "BopomofoLayout",
    "HangulLayout",
    "HangulPreedit",
    "PinyinCorrect",
    "PinyinFuzzy",
    "PinyinScheme",
    "TableInvalid",
    "Width",
    "DEFAULT_MAX_CANDIDATES",
    "has_engine",
    "init",
    "keysym_for_char",
    "load",
    "option_count",
    "option_name",
    "option_value_name",
    "shutdown",
    "version",
    "version_number",
]


# =========================================================================
# Enums mirroring the C ones
# =========================================================================

class EngineId(enum.IntEnum):
    HANGUL = 0
    ANTHY = 1
    PINYIN = 2
    BOPOMOFO = 3
    TABLE = 4


class Requires(enum.IntFlag):
    SURROUNDING_TEXT = 1 << 0
    DELETE_SURROUNDING = 1 << 1


class Mod(enum.IntFlag):
    NONE = 0
    SHIFT = 1 << 0
    CONTROL = 1 << 1
    ALT = 1 << 2
    SUPER = 1 << 3
    CAPS = 1 << 4
    NUMLOCK = 1 << 5


class Key(enum.IntEnum):
    BACKSPACE = 0xFF08
    TAB = 0xFF09
    RETURN = 0xFF0D
    ESCAPE = 0xFF1B
    SPACE = 0x0020
    DELETE = 0xFFFF
    HOME = 0xFF50
    LEFT = 0xFF51
    UP = 0xFF52
    RIGHT = 0xFF53
    DOWN = 0xFF54
    PAGE_UP = 0xFF55
    PAGE_DOWN = 0xFF56
    END = 0xFF57
    MUHENKAN = 0xFF22
    HENKAN = 0xFF23


class OptionType(enum.IntEnum):
    BOOL = 0
    INT = 1
    ENUM = 2
    FLAGS = 3
    STRING = 4


class Option(enum.IntEnum):
    MAX_CANDIDATES = 0
    LEARNING = 1
    LATIN_WIDTH = 2
    PUNCTUATION_WIDTH = 3
    CHINESE_VARIANT = 4
    PREDICTION = 5
    SPECIAL_PHRASES = 6
    INCOMPLETE_INPUT = 7
    HANGUL_LAYOUT = 8
    HANGUL_AUTO_REORDER = 9
    HANGUL_DOUBLE_STROKE_COMBINE = 10
    HANGUL_NON_CHOSEONG_COMBINE = 11
    HANGUL_PREEDIT = 12
    ANTHY_TYPING_METHOD = 13
    ANTHY_KANA_SCRIPT = 14
    ANTHY_PERIOD_STYLE = 15
    ANTHY_SYMBOL_STYLE = 16
    ANTHY_ON_PERIOD = 17
    ANTHY_LATIN_WITH_SHIFT = 18
    PINYIN_SCHEME = 19
    PINYIN_FUZZY = 20
    PINYIN_CORRECTION = 21
    BOPOMOFO_LAYOUT = 22
    TABLE_FILE = 23
    TABLE_AUTO_COMMIT = 24
    TABLE_AUTO_SELECT = 25
    TABLE_SINGLE_WILDCARD = 26
    TABLE_MULTI_WILDCARD = 27
    TABLE_SINGLE_CHAR_ONLY = 28
    TABLE_INVALID_INPUT = 29
    TABLE_PINYIN_FALLBACK = 30


class Width(enum.IntEnum):
    HALF = 0
    FULL = 1


class ChineseVariant(enum.IntEnum):
    SIMPLIFIED_ONLY = 0
    TRADITIONAL_ONLY = 1
    SIMPLIFIED_FIRST = 2
    TRADITIONAL_FIRST = 3
    ANY = 4


class HangulLayout(enum.IntEnum):
    SET2 = 0
    SET2_YET = 1
    SET3_2 = 2
    SET3_390 = 3
    SET3_FINAL = 4
    SET3_NOSHIFT = 5
    SET3_YET = 6
    ROMAJA = 7
    AHNMATAE = 8


class HangulPreedit(enum.IntEnum):
    SYLLABLE = 0
    WORD = 1
    NONE = 2


class AnthyTyping(enum.IntEnum):
    ROMAJI = 0
    KANA = 1


class AnthyScript(enum.IntEnum):
    HIRAGANA = 0
    KATAKANA = 1
    HALFWIDTH_KATAKANA = 2


class AnthyPeriod(enum.IntEnum):
    KUTEN = 0
    FULLWIDTH = 1


class AnthySymbol(enum.IntEnum):
    CORNER_SLASH = 0
    CORNER_MIDDOT = 1
    BRACKET_SLASH = 2
    BRACKET_MIDDOT = 3


class AnthyOnPeriod(enum.IntEnum):
    NOTHING = 0
    CONVERT = 1
    COMMIT = 2


class PinyinScheme(enum.IntEnum):
    FULL = 0
    DOUBLE_MSPY = 1
    DOUBLE_ZRM = 2
    DOUBLE_ABC = 3
    DOUBLE_ZGPY = 4
    DOUBLE_PYJJ = 5
    DOUBLE_XHE = 6


class BopomofoLayout(enum.IntEnum):
    STANDARD = 0
    CHING_YEAH = 1
    ETEN = 2
    IBM = 3


class TableInvalid(enum.IntEnum):
    COMMIT_CANDIDATE = 0
    COMMIT_RAW = 1


class PinyinFuzzy(enum.IntFlag):
    C_CH = 1 << 0
    CH_C = 1 << 1
    Z_ZH = 1 << 2
    ZH_Z = 1 << 3
    S_SH = 1 << 4
    SH_S = 1 << 5
    L_N = 1 << 6
    N_L = 1 << 7
    F_H = 1 << 8
    H_F = 1 << 9
    L_R = 1 << 10
    R_L = 1 << 11
    K_G = 1 << 12
    G_K = 1 << 13
    AN_ANG = 1 << 14
    ANG_AN = 1 << 15
    EN_ENG = 1 << 16
    ENG_EN = 1 << 17
    IN_ING = 1 << 18
    ING_IN = 1 << 19


class PinyinCorrect(enum.IntFlag):
    GN_NG = 1 << 0
    MG_NG = 1 << 1
    IOU_IU = 1 << 2
    UEI_UI = 1 << 3
    UEN_UN = 1 << 4
    UE_VE = 1 << 5
    V_U = 1 << 6
    ON_ONG = 1 << 7


DEFAULT_MAX_CANDIDATES = 64

# Which enum class an ENUM/FLAGS option's values belong to, for typed getters.
_OPTION_VALUE_TYPES: dict[Option, type[enum.IntEnum] | type[enum.IntFlag]] = {
    Option.LATIN_WIDTH: Width,
    Option.PUNCTUATION_WIDTH: Width,
    Option.CHINESE_VARIANT: ChineseVariant,
    Option.HANGUL_LAYOUT: HangulLayout,
    Option.HANGUL_PREEDIT: HangulPreedit,
    Option.ANTHY_TYPING_METHOD: AnthyTyping,
    Option.ANTHY_KANA_SCRIPT: AnthyScript,
    Option.ANTHY_PERIOD_STYLE: AnthyPeriod,
    Option.ANTHY_SYMBOL_STYLE: AnthySymbol,
    Option.ANTHY_ON_PERIOD: AnthyOnPeriod,
    Option.PINYIN_SCHEME: PinyinScheme,
    Option.PINYIN_FUZZY: PinyinFuzzy,
    Option.PINYIN_CORRECTION: PinyinCorrect,
    Option.BOPOMOFO_LAYOUT: BopomofoLayout,
    Option.TABLE_INVALID_INPUT: TableInvalid,
}


# =========================================================================
# Errors
# =========================================================================

class Error(Exception):
    """Base of every libpathime error. ``status`` is the C status code."""

    status: int = -1

    def __init__(self, message: str | None = None):
        super().__init__(message or self.__doc__)


class InvalidArgumentError(Error):
    """NULL handle, bad index, bad UTF-8, or bad struct_size."""
    status = 1


class UnknownEngineError(Error):
    """Engine not available in this library."""
    status = 2


class MissingCallbackError(Error):
    """Client lacks a callback the engine requires."""
    status = 3


class UnsupportedError(Error):
    """Engine does not implement this operation."""
    status = 4


class NotInitializedError(Error):
    """pathime.init() has not been called."""
    status = 5


class AlreadyInitializedError(Error):
    """pathime.init() has already succeeded."""
    status = 6


class OutOfMemoryError(Error):
    """Allocation failed; composition state is indeterminate until reset."""
    status = 7


class BackendError(Error):
    """Backend library or data file failure; composition state is
    indeterminate until reset."""
    status = 8


_ERRORS = {
    e.status: e
    for e in (
        InvalidArgumentError, UnknownEngineError, MissingCallbackError,
        UnsupportedError, NotInitializedError, AlreadyInitializedError,
        OutOfMemoryError, BackendError,
    )
}


def _check(status: int) -> None:
    if status == 0:
        return
    cls = _ERRORS.get(status, Error)
    message = None
    if _the_lib is not None:
        message = _the_lib.pathime_status_string(status).decode("utf-8")
    raise cls(message)


# =========================================================================
# Library handle
# =========================================================================

_the_lib: ctypes.CDLL | None = None


def load(path: str | None = None) -> None:
    """Load the shared library explicitly.

    Optional: the first call that needs the library loads it using
    ``PATHIME_LIBRARY`` or the system loader. Call this to name a path in
    code instead. It is an error to load twice.
    """
    global _the_lib
    if _the_lib is not None:
        raise Error("libpathime is already loaded")
    _the_lib = _ffi.load_library(path)


def _lib() -> ctypes.CDLL:
    global _the_lib
    if _the_lib is None:
        _the_lib = _ffi.load_library()
    return _the_lib


# =========================================================================
# Module-level functions
# =========================================================================

def version() -> str:
    """The loaded library's version, e.g. ``"0.1.0"``."""
    return _lib().pathime_version_string().decode("utf-8")


def version_number() -> int:
    """The loaded library's version as a comparable integer
    (major*1000000 + minor*1000 + patch)."""
    return _lib().pathime_version()


def init(data_dir: str | None = None, resource_dir: str | None = None) -> None:
    """Initialize process-global state. Must succeed before engines exist.

    :param data_dir: directory the library may read and write (learned
        frequencies, user dictionaries). None selects the library default.
    :param resource_dir: directory holding the shipped read-only data. None
        selects ``pathime-data`` beside the libpathime binary.
    """
    lib = _lib()
    params = _ffi.pathime_init_params_t(
        ctypes.sizeof(_ffi.pathime_init_params_t),
        data_dir.encode("utf-8") if data_dir is not None else None,
        resource_dir.encode("utf-8") if resource_dir is not None else None,
    )
    _check(lib.pathime_init(ctypes.byref(params)))


def shutdown() -> None:
    """Release process-global state. Engines and contexts must be closed."""
    _lib().pathime_shutdown()


def has_engine(engine_id: EngineId) -> bool:
    """True iff :class:`Engine` can currently be created for ``engine_id``."""
    return bool(_lib().pathime_has_engine(int(engine_id)))


def option_count() -> int:
    """How many options the library defines; ids are dense from 0."""
    return _lib().pathime_option_count()


def option_name(option: Option | int) -> str:
    """Stable machine-readable option name, e.g. ``"chinese-variant"``.
    ``""`` for a value that is not an option id."""
    return _lib().pathime_option_name(int(option)).decode("utf-8")


def option_value_name(option: Option | int, value: int) -> str:
    """Stable machine-readable name of one option value, ``""`` where the
    value has no name (BOOL and INT options, unknown values)."""
    return _lib().pathime_option_value_name(int(option), int(value)).decode("utf-8")


def keysym_for_char(char: str) -> int:
    """The X11 keysym for a printable character: the scalar value below
    U+0100, ``0x01000000 + scalar`` at or above it."""
    cp = ord(char)
    return cp if cp < 0x100 else 0x01000000 + cp


# =========================================================================
# Data carried across the boundary
# =========================================================================

@dataclass(frozen=True)
class KeyEvent:
    """One key press. ``keysym`` may be given as a one-character string.

    ``layout_key`` names the physical key as the keysym it would produce
    unmodified on US QWERTY, 0 when there is no physical key to report.
    """

    keysym: int | str
    layout_key: int | str = 0
    modifiers: Mod = Mod.NONE

    def _to_c(self) -> _ffi.pathime_key_event_t:
        keysym = (keysym_for_char(self.keysym)
                  if isinstance(self.keysym, str) else int(self.keysym))
        layout = (keysym_for_char(self.layout_key)
                  if isinstance(self.layout_key, str) else int(self.layout_key))
        return _ffi.pathime_key_event_t(
            ctypes.sizeof(_ffi.pathime_key_event_t),
            keysym, layout, int(self.modifiers))


@dataclass(frozen=True)
class Composition:
    """A copied snapshot of a context's composition state.

    Unlike the C struct this includes the candidate texts themselves: they are
    materialized before the library announces a change, so copying them costs
    one pass and frees the client from borrowed-lifetime rules entirely.
    """

    preedit: str = ""
    preedit_settled: int = 0
    candidates: tuple[str, ...] = ()
    candidate_cursor: int = 0

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)


@dataclass(frozen=True)
class OptionInfo:
    """Everything needed to present an option without knowing it by name."""

    type: OptionType
    supported: bool
    resets_composition: bool
    default: bool | int | str
    min_value: int
    max_value: int
    valid_values: int
    valid_value_count: int


# =========================================================================
# Option access shared by Engine and Context
# =========================================================================

class _OptionAccess:
    """get/set/reset options; the C level (engine vs context) comes from
    ``_PREFIX`` and ``_handle`` on the concrete class."""

    _PREFIX: str
    _handle: ctypes.c_void_p

    def _post_mutate(self) -> None:
        raise NotImplementedError

    def _info_engine_handle(self) -> ctypes.c_void_p:
        raise NotImplementedError

    def option_info(self, option: Option) -> OptionInfo:
        """Describe ``option`` as this engine implements it."""
        lib = _lib()
        raw = _ffi.pathime_option_info_t()
        raw.struct_size = ctypes.sizeof(raw)
        _check(lib.pathime_engine_option_info(
            self._info_engine_handle(), int(option), ctypes.byref(raw)))
        otype = OptionType(raw.type)
        default: bool | int | str
        if otype == OptionType.STRING:
            default = raw.default_string.to_str()
        elif otype == OptionType.BOOL:
            default = bool(raw.default_value)
        else:
            default = int(raw.default_value)
        return OptionInfo(
            type=otype,
            supported=raw.supported,
            resets_composition=raw.resets_composition,
            default=default,
            min_value=raw.min_value,
            max_value=raw.max_value,
            valid_values=raw.valid_values,
            valid_value_count=raw.valid_value_count,
        )

    def set_option(self, option: Option, value: bool | int | str | enum.IntEnum) -> None:
        """Set an option, dispatching on its declared type.

        ``bool`` options take bools; INT, ENUM and FLAGS take ints (enum
        members are ints); STRING takes str.
        """
        lib = _lib()
        if isinstance(value, str):
            status = getattr(lib, f"{self._PREFIX}_set_option_string")(
                self._handle, int(option), value.encode("utf-8"))
        elif isinstance(value, bool):
            status = getattr(lib, f"{self._PREFIX}_set_option_bool")(
                self._handle, int(option), value)
        else:
            status = getattr(lib, f"{self._PREFIX}_set_option_int")(
                self._handle, int(option), int(value))
        self._post_mutate()
        _check(status)

    def get_option(self, option: Option) -> bool | int | str | enum.IntEnum:
        """The resolved effective value, typed by the option's declared type:
        bool, int, str, or the mirroring enum/flag member."""
        lib = _lib()
        otype = self.option_info(option).type
        if otype == OptionType.STRING:
            out = _ffi.pathime_str_t()
            _check(getattr(lib, f"{self._PREFIX}_get_option_string")(
                self._handle, int(option), ctypes.byref(out)))
            return out.to_str()
        if otype == OptionType.BOOL:
            bout = ctypes.c_bool()
            _check(getattr(lib, f"{self._PREFIX}_get_option_bool")(
                self._handle, int(option), ctypes.byref(bout)))
            return bout.value
        iout = ctypes.c_int64()
        _check(getattr(lib, f"{self._PREFIX}_get_option_int")(
            self._handle, int(option), ctypes.byref(iout)))
        value = iout.value
        enum_cls = _OPTION_VALUE_TYPES.get(Option(option))
        return enum_cls(value) if enum_cls is not None else value

    def reset_option(self, option: Option) -> None:
        """Drop the value set at this level; resolve from the next tier."""
        lib = _lib()
        status = getattr(lib, f"{self._PREFIX}_reset_option")(
            self._handle, int(option))
        self._post_mutate()
        _check(status)

    def option_is_set(self, option: Option) -> bool:
        """True iff a value was explicitly set at this level."""
        lib = _lib()
        return bool(getattr(lib, f"{self._PREFIX}_option_is_set")(
            self._handle, int(option)))


# =========================================================================
# Engine
# =========================================================================

class Engine(_OptionAccess):
    """One input method implementation plus state shared across contexts.

    Comparatively expensive; create one per input method and share it. Close
    (or leave a ``with`` block) after every context created from it is closed.
    """

    _PREFIX = "pathime_engine"

    def __init__(self, engine_id: EngineId):
        self._handle = None
        lib = _lib()
        handle = ctypes.c_void_p()
        _check(lib.pathime_engine_create(int(engine_id), ctypes.byref(handle)))
        self._handle = handle
        self._contexts: weakref.WeakSet[Context] = weakref.WeakSet()

    @property
    def id(self) -> EngineId:
        return EngineId(_lib().pathime_engine_id(self._handle))

    @property
    def requirements(self) -> Requires:
        """What this engine needs from its client, resolved against the
        engine's own configuration."""
        return Requires(_lib().pathime_engine_requirements(self._handle))

    def close(self) -> None:
        """Destroy the engine. Every context created from it must already be
        closed. Safe to call twice."""
        if self._handle is not None:
            _lib().pathime_engine_destroy(self._handle)
            self._handle = None

    def __enter__(self) -> "Engine":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # An engine-level option set dispatches composition_changed to every
    # inheriting context; surface any exception those callbacks raised.
    def _post_mutate(self) -> None:
        for ctx in list(self._contexts):
            ctx._raise_pending()

    def _info_engine_handle(self) -> ctypes.c_void_p:
        return self._handle


# =========================================================================
# Context
# =========================================================================

class Context(_OptionAccess):
    """One independently editable client destination.

    Callbacks are constructor arguments:

    - ``on_commit(text: str)`` — finalized text to insert. Optional: without
      it, committed text accumulates and :meth:`take_committed` drains it.
    - ``on_delete_surrounding(offset: int, count: int)`` — delete ``count``
      scalar values starting ``offset`` from the cursor position last given to
      :meth:`set_surrounding_text`. Only supplied to the library when given
      here, so an engine that requires it still fails loudly when it is
      missing.
    - ``on_composition_changed(composition: Composition)`` — the composition
      was replaced. The snapshot is fully copied, candidates included.

    The current snapshot is always readable as :attr:`composition`.

    Exceptions raised inside callbacks cannot cross the C library; they are
    caught, the dispatch continues, and the first one is re-raised once the
    triggering call returns.
    """

    _PREFIX = "pathime_context"

    def __init__(
        self,
        engine: Engine,
        on_commit=None,
        on_delete_surrounding=None,
        on_composition_changed=None,
    ):
        self._handle = None
        self._engine = engine
        self._on_commit = on_commit
        self._on_delete_surrounding = on_delete_surrounding
        self._on_composition_changed = on_composition_changed
        self._committed: list[str] = []
        self._composition = Composition()
        self._pending_error: BaseException | None = None

        lib = _lib()

        # The C callbacks. Kept as attributes for the context's lifetime:
        # the library holds only the pointer.
        def commit_text(user_data, text: _ffi.pathime_str_t) -> None:
            try:
                s = text.to_str()
                if self._on_commit is not None:
                    self._on_commit(s)
                else:
                    self._committed.append(s)
            except BaseException as e:  # noqa: BLE001 — deferred, not dropped
                if self._pending_error is None:
                    self._pending_error = e

        def delete_surrounding(user_data, offset: int, count: int) -> None:
            try:
                self._on_delete_surrounding(offset, count)
            except BaseException as e:  # noqa: BLE001
                if self._pending_error is None:
                    self._pending_error = e

        def composition_changed(user_data, comp_p) -> None:
            try:
                comp = comp_p.contents
                candidates = []
                out = _ffi.pathime_str_t()
                for i in range(comp.candidate_count):
                    # Callback-safe: candidates are materialized before the
                    # library dispatches this callback.
                    if lib.pathime_context_candidate(
                            self._handle, i, ctypes.byref(out)) == 0:
                        candidates.append(out.to_str())
                self._composition = Composition(
                    preedit=comp.preedit.to_str(),
                    preedit_settled=comp.preedit_settled,
                    candidates=tuple(candidates),
                    candidate_cursor=comp.candidate_cursor,
                )
                if self._on_composition_changed is not None:
                    self._on_composition_changed(self._composition)
            except BaseException as e:  # noqa: BLE001
                if self._pending_error is None:
                    self._pending_error = e

        self._c_commit = _ffi.COMMIT_TEXT_FN(commit_text)
        self._c_delete = (_ffi.DELETE_SURROUNDING_FN(delete_surrounding)
                          if on_delete_surrounding is not None
                          else _ffi.DELETE_SURROUNDING_FN())
        self._c_changed = _ffi.COMPOSITION_CHANGED_FN(composition_changed)
        self._client = _ffi.pathime_client_t(
            ctypes.sizeof(_ffi.pathime_client_t),
            self._c_commit, self._c_delete, self._c_changed)

        handle = ctypes.c_void_p()
        _check(lib.pathime_context_create(
            engine._handle, ctypes.byref(self._client), None,
            ctypes.byref(handle)))
        self._handle = handle
        engine._contexts.add(self)

    # ---- lifecycle ----

    def close(self) -> None:
        """Destroy the context, discarding composition state without
        committing it. Safe to call twice."""
        if self._handle is not None:
            _lib().pathime_context_destroy(self._handle)
            self._handle = None

    def __enter__(self) -> "Context":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ---- callback error deferral ----

    def _raise_pending(self) -> None:
        if self._pending_error is not None:
            e, self._pending_error = self._pending_error, None
            raise e

    def _mutate(self, status: int) -> None:
        self._raise_pending()
        _check(status)

    def _post_mutate(self) -> None:
        self._raise_pending()

    def _info_engine_handle(self) -> ctypes.c_void_p:
        return self._engine._handle

    # ---- properties ----

    @property
    def engine(self) -> Engine:
        return self._engine

    @property
    def requirements(self) -> Requires:
        """What this context needs from its client, resolved against its own
        settings."""
        return Requires(_lib().pathime_context_requirements(self._handle))

    @property
    def composition(self) -> Composition:
        """The current composition snapshot (kept current by the library's
        own change announcements)."""
        return self._composition

    @property
    def committed(self) -> str:
        """Text committed so far and not yet drained, when no ``on_commit``
        callback was given."""
        return "".join(self._committed)

    def take_committed(self) -> str:
        """Return :attr:`committed` and clear it."""
        text = "".join(self._committed)
        self._committed.clear()
        return text

    # ---- input ----

    def process_key(self, key: KeyEvent | str | int,
                    modifiers: Mod = Mod.NONE,
                    layout_key: int | str = 0) -> bool:
        """Offer one key press to the engine; True iff it was handled.

        ``key`` may be a :class:`KeyEvent`, a one-character string, or a
        keysym (:class:`Key` or int). All output the key produced has been
        dispatched by the time this returns.
        """
        if not isinstance(key, KeyEvent):
            key = KeyEvent(key, layout_key=layout_key, modifiers=modifiers)
        event = key._to_c()
        handled = ctypes.c_bool(False)
        status = _lib().pathime_context_process_key(
            self._handle, ctypes.byref(event), ctypes.byref(handled))
        self._mutate(status)
        return handled.value

    def type(self, text: str) -> None:
        """Convenience: offer each character of ``text`` as a key press."""
        for ch in text:
            self.process_key(ch)

    # ---- candidates ----

    def candidate(self, index: int) -> str:
        """One candidate by absolute position, copied."""
        out = _ffi.pathime_str_t()
        _check(_lib().pathime_context_candidate(
            self._handle, index, ctypes.byref(out)))
        return out.to_str()

    def set_candidate_cursor(self, index: int) -> None:
        """Move the highlight to absolute position ``index`` without choosing
        it. Redraw from :attr:`composition`; the engine may move the cursor
        itself."""
        self._mutate(_lib().pathime_context_set_candidate_cursor(
            self._handle, index))

    def select_candidate(self, index: int) -> None:
        """Choose the candidate at absolute position ``index``, settling the
        span it covers."""
        self._mutate(_lib().pathime_context_select_candidate(
            self._handle, index))

    # ---- client text ----

    def set_surrounding_text(self, text: str, cursor: int) -> None:
        """Supply text near the insertion position; ``cursor`` is a position
        in ``text`` as a Python string index."""
        if not 0 <= cursor <= len(text):
            raise InvalidArgumentError(
                "cursor %d outside text of %d characters" % (cursor, len(text)))
        data = text.encode("utf-8")
        self._mutate(_lib().pathime_context_set_surrounding_text(
            self._handle, _ffi.make_str(data), cursor))

    def commit(self) -> None:
        """End the composition now, committing what it holds. A no-op on an
        empty composition."""
        self._mutate(_lib().pathime_context_commit(self._handle))

    def reset(self) -> None:
        """Discard composition state; commit nothing. Also the recovery path
        after :class:`OutOfMemoryError` or :class:`BackendError`."""
        self._mutate(_lib().pathime_context_reset(self._handle))
