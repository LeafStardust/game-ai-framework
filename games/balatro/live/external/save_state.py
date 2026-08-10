from __future__ import annotations

import hashlib
import os
import time
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class BalatroSaveError(RuntimeError):
    pass


@dataclass(frozen=True)
class BalatroSaveSnapshot:
    path: Path
    modified_ns: int
    size: int
    sha256: str
    data: dict[str | int, Any]


def discover_balatro_save_paths(appdata: str | Path | None = None) -> list[Path]:
    root = Path(appdata) if appdata is not None else _default_appdata()
    balatro_root = root / "Balatro"
    candidates = list(balatro_root.glob("*/save.jkr"))
    root_save = balatro_root / "save.jkr"
    if root_save.is_file():
        candidates.append(root_save)
    return sorted(
        {path.resolve() for path in candidates if path.is_file()},
        key=lambda path: (path.parent.name, str(path)),
    )


def resolve_balatro_save_path(
    path: str | Path | None = None,
    *,
    profile: str | int | None = "1",
    appdata: str | Path | None = None,
) -> Path:
    if path is not None:
        resolved = Path(path).expanduser().resolve()
        if not resolved.is_file():
            raise BalatroSaveError(f"Balatro save file not found: {resolved}")
        return resolved

    root = Path(appdata) if appdata is not None else _default_appdata()
    if profile is not None:
        preferred = (root / "Balatro" / str(profile) / "save.jkr").resolve()
        if preferred.is_file():
            return preferred

    candidates = discover_balatro_save_paths(root)
    if not candidates:
        raise BalatroSaveError(
            f"no save.jkr found under {(root / 'Balatro').resolve()}"
        )
    if len(candidates) == 1:
        return candidates[0]

    newest = max(candidates, key=lambda candidate: candidate.stat().st_mtime_ns)
    return newest


def decode_balatro_save(raw: bytes) -> dict[str | int, Any]:
    if not raw:
        raise BalatroSaveError("Balatro save file is empty")
    try:
        text = zlib.decompress(raw, wbits=-zlib.MAX_WBITS).decode("utf-8")
    except (UnicodeDecodeError, zlib.error) as error:
        raise BalatroSaveError("unable to decompress Balatro save.jkr") from error

    parser = _LuaValueParser(text)
    value = parser.parse_document()
    if not isinstance(value, dict):
        raise BalatroSaveError("Balatro save root is not a keyed table")
    return value


class BalatroSaveReader:

    def __init__(
        self,
        path: str | Path | None = None,
        *,
        profile: str | int | None = "1",
        appdata: str | Path | None = None,
    ):
        self.path = resolve_balatro_save_path(
            path,
            profile=profile,
            appdata=appdata,
        )

    def read(self, *, retries: int = 4, retry_delay: float = 0.05) -> BalatroSaveSnapshot:
        attempts = max(1, retries)
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                stat_before = self.path.stat()
                raw = self.path.read_bytes()
                stat_after = self.path.stat()
                if (
                    stat_before.st_mtime_ns != stat_after.st_mtime_ns
                    or stat_before.st_size != stat_after.st_size
                ):
                    raise BalatroSaveError("Balatro save changed while being read")
                data = decode_balatro_save(raw)
                return BalatroSaveSnapshot(
                    path=self.path,
                    modified_ns=stat_after.st_mtime_ns,
                    size=len(raw),
                    sha256=hashlib.sha256(raw).hexdigest(),
                    data=data,
                )
            except (OSError, BalatroSaveError) as error:
                last_error = error
                if attempt + 1 < attempts and retry_delay > 0:
                    time.sleep(retry_delay)
        raise BalatroSaveError(f"unable to read Balatro save: {self.path}") from last_error


def summarize_balatro_save(snapshot: BalatroSaveSnapshot) -> dict[str, Any]:
    data = snapshot.data
    game = _mapping(data.get("GAME"))
    blind = _mapping(data.get("BLIND"))
    back = _mapping(data.get("BACK"))
    round_resets = _mapping(game.get("round_resets"))
    current_round = _mapping(game.get("current_round"))
    card_areas = _mapping(data.get("cardAreas"))

    hand_cards = _area_cards(card_areas, "hand")
    deck_cards = _area_cards(card_areas, "deck")
    play_cards = _area_cards(card_areas, "play")
    joker_cards = _area_cards(card_areas, "jokers")
    consumable_cards = _area_cards(card_areas, "consumeables")
    if not consumable_cards:
        consumable_cards = _area_cards(card_areas, "consumables")

    return {
        "path": str(snapshot.path),
        "modified_ns": snapshot.modified_ns,
        "size": snapshot.size,
        "sha256": snapshot.sha256,
        "version": data.get("VERSION"),
        "state": data.get("STATE"),
        "top_level_keys": sorted(str(key) for key in data),
        "run": {
            "ante": round_resets.get("ante"),
            "round": game.get("round"),
            "money": game.get("dollars"),
            "score": game.get("chips"),
            "blind_name": blind.get("name") or game.get("blind"),
            "blind_target": blind.get("chips"),
            "hands_left": current_round.get("hands_left"),
            "discards_left": current_round.get("discards_left"),
            "deck_name": back.get("name") or back.get("key"),
            "stake": game.get("stake"),
            "won": game.get("won"),
        },
        "areas": {
            "hand": len(hand_cards),
            "deck": len(deck_cards),
            "play": len(play_cards),
            "jokers": len(joker_cards),
            "consumables": len(consumable_cards),
            "keys": sorted(str(key) for key in card_areas),
        },
        "hand": [_card_label(card) for card in hand_cards],
        "jokers": [_card_label(card) for card in joker_cards],
        "consumables": [_card_label(card) for card in consumable_cards],
    }


def _default_appdata() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata)
    if os.name == "posix":
        mac = Path.home() / "Library" / "Application Support"
        if mac.exists():
            return mac
    raise BalatroSaveError("APPDATA is unavailable; pass an explicit save path")


def _mapping(value: Any) -> dict[Any, Any]:
    return value if isinstance(value, dict) else {}


def _area_cards(card_areas: dict[Any, Any], name: str) -> list[dict[Any, Any]]:
    area = _mapping(card_areas.get(name))
    cards = area.get("cards", [])
    if isinstance(cards, list):
        return [card for card in cards if isinstance(card, dict)]
    if isinstance(cards, dict):
        ordered = []
        for key in sorted(cards, key=lambda value: (not isinstance(value, int), str(value))):
            card = cards[key]
            if isinstance(card, dict):
                ordered.append(card)
        return ordered
    return []


def _card_label(card: dict[Any, Any]) -> str:
    label = card.get("label")
    if isinstance(label, str) and label:
        return label
    base = _mapping(card.get("base"))
    name = base.get("name")
    if isinstance(name, str) and name:
        return name
    value = base.get("value")
    suit = base.get("suit")
    if value is not None and suit is not None:
        return f"{value} of {suit}"
    save_fields = _mapping(card.get("save_fields"))
    center = save_fields.get("center")
    card_key = save_fields.get("card")
    if card_key is not None:
        return str(card_key)
    if center is not None:
        return str(center)
    return "unknown"


class _LuaValueParser:

    def __init__(self, text: str):
        self.text = text
        self.index = 0

    def parse_document(self) -> Any:
        self._skip_space()
        if self._peek_identifier("return"):
            self._parse_identifier()
        value = self._parse_value()
        self._skip_space()
        if self.index != len(self.text):
            raise BalatroSaveError(
                f"unexpected save data at offset {self.index}"
            )
        return value

    def _parse_value(self) -> Any:
        self._skip_space()
        if self.index >= len(self.text):
            raise BalatroSaveError("unexpected end of Balatro save data")
        char = self.text[self.index]
        if char == "{":
            return self._parse_table()
        if char in ('"', "'"):
            return self._parse_string()
        if char.isdigit() or char in "+-.":
            return self._parse_number()
        identifier = self._parse_identifier()
        if identifier == "true":
            return True
        if identifier == "false":
            return False
        if identifier == "nil":
            return None
        raise BalatroSaveError(f"unsupported Lua value {identifier!r}")

    def _parse_table(self) -> Any:
        self._expect("{")
        entries: list[tuple[Any, Any]] = []
        next_array_index = 1
        self._skip_space()

        while not self._consume("}"):
            self._skip_space()
            if self._consume("["):
                key = self._parse_value()
                self._skip_space()
                self._expect("]")
                self._skip_space()
                self._expect("=")
                value = self._parse_value()
            else:
                checkpoint = self.index
                key = None
                if self.index < len(self.text) and (
                    self.text[self.index].isalpha() or self.text[self.index] == "_"
                ):
                    identifier = self._parse_identifier()
                    self._skip_space()
                    if self._consume("="):
                        key = identifier
                        value = self._parse_value()
                    else:
                        self.index = checkpoint
                        value = self._parse_value()
                else:
                    value = self._parse_value()
                if key is None:
                    key = next_array_index
                    next_array_index += 1

            entries.append((key, value))
            self._skip_space()
            if self._consume(",") or self._consume(";"):
                self._skip_space()
                continue
            if self._peek("}"):
                continue
            raise BalatroSaveError(
                f"expected table separator at offset {self.index}"
            )

        if not entries:
            return {}
        if all(isinstance(key, int) and not isinstance(key, bool) for key, _ in entries):
            keys = [key for key, _ in entries]
            if sorted(keys) == list(range(1, len(entries) + 1)) and len(set(keys)) == len(keys):
                by_key = {key: value for key, value in entries}
                return [by_key[index] for index in range(1, len(entries) + 1)]

        result: dict[Any, Any] = {}
        for key, value in entries:
            try:
                result[key] = value
            except TypeError as error:
                raise BalatroSaveError("Balatro save contains an unhashable table key") from error
        return result

    def _parse_string(self) -> str:
        quote = self.text[self.index]
        self.index += 1
        output: list[str] = []
        escapes = {
            "a": "\a",
            "b": "\b",
            "f": "\f",
            "n": "\n",
            "r": "\r",
            "t": "\t",
            "v": "\v",
            "\\": "\\",
            '"': '"',
            "'": "'",
        }

        while self.index < len(self.text):
            char = self.text[self.index]
            self.index += 1
            if char == quote:
                return "".join(output)
            if char != "\\":
                output.append(char)
                continue
            if self.index >= len(self.text):
                raise BalatroSaveError("unterminated escape sequence in save string")
            escaped = self.text[self.index]
            self.index += 1
            if escaped in escapes:
                output.append(escapes[escaped])
                continue
            if escaped == "x":
                token = self.text[self.index : self.index + 2]
                if len(token) != 2 or any(char not in "0123456789abcdefABCDEF" for char in token):
                    raise BalatroSaveError("invalid hexadecimal escape in save string")
                self.index += 2
                output.append(chr(int(token, 16)))
                continue
            if escaped.isdigit():
                digits = escaped
                while len(digits) < 3 and self.index < len(self.text) and self.text[self.index].isdigit():
                    digits += self.text[self.index]
                    self.index += 1
                output.append(chr(int(digits, 10)))
                continue
            if escaped == "\n":
                continue
            output.append(escaped)
        raise BalatroSaveError("unterminated string in Balatro save")

    def _parse_number(self) -> int | float:
        start = self.index
        allowed = set("0123456789+-.eE")
        while self.index < len(self.text) and self.text[self.index] in allowed:
            self.index += 1
        token = self.text[start : self.index]
        if not token or token in {"+", "-", ".", "+.", "-."}:
            raise BalatroSaveError(f"invalid number at offset {start}")
        try:
            if any(char in token for char in ".eE"):
                return float(token)
            return int(token)
        except ValueError as error:
            raise BalatroSaveError(f"invalid number {token!r}") from error

    def _parse_identifier(self) -> str:
        self._skip_space()
        start = self.index
        if self.index >= len(self.text) or not (
            self.text[self.index].isalpha() or self.text[self.index] == "_"
        ):
            raise BalatroSaveError(f"expected Lua identifier at offset {self.index}")
        self.index += 1
        while self.index < len(self.text) and (
            self.text[self.index].isalnum() or self.text[self.index] == "_"
        ):
            self.index += 1
        return self.text[start : self.index]

    def _skip_space(self) -> None:
        while self.index < len(self.text) and self.text[self.index].isspace():
            self.index += 1

    def _consume(self, token: str) -> bool:
        self._skip_space()
        if self.text.startswith(token, self.index):
            self.index += len(token)
            return True
        return False

    def _expect(self, token: str) -> None:
        if not self._consume(token):
            raise BalatroSaveError(
                f"expected {token!r} at offset {self.index}"
            )

    def _peek(self, token: str) -> bool:
        self._skip_space()
        return self.text.startswith(token, self.index)

    def _peek_identifier(self, token: str) -> bool:
        self._skip_space()
        if not self.text.startswith(token, self.index):
            return False
        end = self.index + len(token)
        return end == len(self.text) or not (
            self.text[end].isalnum() or self.text[end] == "_"
        )
