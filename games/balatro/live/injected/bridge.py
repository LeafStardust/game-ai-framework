from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Iterable


class InjectedBridgeError(RuntimeError):
    pass


class InjectedBridgeTimeoutError(InjectedBridgeError):
    pass


class InjectedBridgeProtocolError(InjectedBridgeError):
    pass


def default_bridge_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise InjectedBridgeError("APPDATA is not available")
    return Path(appdata) / "Balatro" / "game-ai-framework-bridge"


def _validated_indices(values: Iterable[int]) -> tuple[int, ...]:
    indices = tuple(int(value) for value in values)
    if not indices:
        raise ValueError("at least one hand index is required")
    if any(index < 0 for index in indices):
        raise ValueError("hand indices cannot be negative")
    if len(set(indices)) != len(indices):
        raise ValueError("hand indices cannot contain duplicates")
    return indices


def _validated_index(value: int) -> int:
    if isinstance(value, bool):
        raise ValueError("boolean is not a valid action index")
    index = int(value)
    if index < 0:
        raise ValueError("action index cannot be negative")
    return index


def encode_command(command_id: str, action: str, indices: Iterable[int] = ()) -> str:
    normalized_action = str(action).strip().upper()
    if not command_id or any(char in command_id for char in "\t\r\n"):
        raise ValueError("command id must be a non-empty single field")
    if not normalized_action or any(
        char in normalized_action for char in "\t\r\n"
    ):
        raise ValueError("action must be a non-empty single field")
    values = tuple(int(value) for value in indices)
    payload = ",".join(str(value) for value in values)
    return f"{command_id}\t{normalized_action}\t{payload}\n"


def parse_response(text: str) -> tuple[str, str, str]:
    line = str(text).strip("\r\n")
    parts = line.split("\t", 2)
    if len(parts) < 2:
        raise InjectedBridgeProtocolError(
            "injected bridge response is malformed"
        )
    command_id, status = parts[0], parts[1].upper()
    message = parts[2] if len(parts) == 3 else ""
    if not command_id:
        raise InjectedBridgeProtocolError(
            "injected bridge response has no command id"
        )
    if status not in {"OK", "ERROR"}:
        raise InjectedBridgeProtocolError(
            f"injected bridge returned unknown status {status!r}"
        )
    return command_id, status, message


def parse_status_message(message: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for item in str(message).split(";"):
        if not item:
            continue
        if "=" not in item:
            raise InjectedBridgeProtocolError(
                "injected bridge status field is malformed"
            )
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or not value:
            raise InjectedBridgeProtocolError(
                "injected bridge status field is empty"
            )
        if key in fields:
            raise InjectedBridgeProtocolError(
                f"injected bridge status repeats field {key!r}"
            )
        fields[key] = value
    if not fields:
        raise InjectedBridgeProtocolError(
            "injected bridge returned empty status"
        )
    return fields


class FirstPartyBalatroBridge:
    """File-command client for the repo-owned in-process Balatro Lua bridge.

    The Lua side is loaded from the patched fused LÖVE archive and runs on
    Balatro's normal game thread. Python never writes gameplay memory directly.
    State verification remains the responsibility of the read-only live-memory
    observer for gameplay actions.
    """

    def __init__(
        self,
        bridge_dir: str | Path | None = None,
        *,
        timeout: float = 2.0,
        poll_interval: float = 0.01,
    ) -> None:
        self.bridge_dir = (
            Path(bridge_dir)
            if bridge_dir is not None
            else default_bridge_dir()
        )
        self.timeout = max(0.0, float(timeout))
        self.poll_interval = max(0.0, float(poll_interval))
        self.command_path = self.bridge_dir / "command.txt"
        self.response_path = self.bridge_dir / "response.txt"

    def ping(self) -> None:
        self._call("PING")

    def status(self) -> dict[str, str]:
        return parse_status_message(self._call("STATUS"))

    def is_connected(self) -> bool:
        try:
            self.ping()
        except InjectedBridgeError:
            return False
        return True

    def play(self, indices: Iterable[int]) -> None:
        self._call("PLAY", _validated_indices(indices))

    def discard(self, indices: Iterable[int]) -> None:
        self._call("DISCARD", _validated_indices(indices))

    def use_consumable(
        self,
        consumable_index: int,
        hand_indices: Iterable[int] = (),
    ) -> None:
        slot = _validated_index(consumable_index)
        targets = tuple(int(value) for value in hand_indices)
        if targets:
            targets = _validated_indices(targets)
        # Consumable slots and hand-card positions are independent zero-based
        # coordinate spaces. A slot and target may therefore share the same
        # numeric index; validate target uniqueness separately before encoding.
        self._call("USE_CONSUMABLE", (slot, *targets))

    def cash_out(self) -> None:
        self._call("CASH_OUT")

    def next_round(self) -> None:
        self._call("NEXT_ROUND")

    def select_blind(self) -> None:
        self._call("SELECT_BLIND")

    def reroll_shop(self) -> None:
        self._call("REROLL_SHOP")

    def buy_shop_card(self, index: int) -> None:
        self._call("BUY_CARD", (_validated_index(index),))

    def buy_and_use_shop_consumable(self, index: int) -> None:
        self._call(
            "BUY_AND_USE_CONSUMABLE",
            (_validated_index(index),),
        )

    def buy_voucher(self, index: int) -> None:
        self._call("BUY_VOUCHER", (_validated_index(index),))

    def buy_booster(self, index: int) -> None:
        self._call("BUY_BOOSTER", (_validated_index(index),))

    def sell_joker(self, index: int) -> None:
        self._call("SELL_JOKER", (_validated_index(index),))

    def select_pack_card(
        self,
        index: int,
        hand_indices: Iterable[int] = (),
    ) -> None:
        pack_index = _validated_index(index)
        targets = tuple(int(value) for value in hand_indices)
        if targets:
            targets = _validated_indices(targets)
        # Pack slots and hand-card positions are independent zero-based spaces.
        self._call("PACK_SELECT", (pack_index, *targets))

    def skip_booster(self) -> None:
        self._call("PACK_SKIP")

    def _call(
        self,
        action: str,
        indices: Iterable[int] = (),
    ) -> str:
        self.bridge_dir.mkdir(parents=True, exist_ok=True)

        if self.command_path.exists():
            raise InjectedBridgeProtocolError(
                "injected bridge command slot is occupied; "
                "remove the stale command only after confirming Balatro "
                "is not processing it"
            )

        command_id = uuid.uuid4().hex
        command = encode_command(command_id, action, indices)

        try:
            self.response_path.unlink(missing_ok=True)
        except OSError as error:
            raise InjectedBridgeError(
                f"unable to clear stale injected bridge response: {error}"
            ) from error

        temporary = self.bridge_dir / f"command.{command_id}.tmp"
        try:
            temporary.write_text(
                command,
                encoding="utf-8",
                newline="\n",
            )
            os.replace(temporary, self.command_path)
        except OSError as error:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise InjectedBridgeError(
                f"unable to submit injected bridge command: {error}"
            ) from error

        deadline = time.monotonic() + self.timeout
        while True:
            if self.response_path.exists():
                try:
                    response_text = self.response_path.read_text(
                        encoding="utf-8"
                    )
                except OSError:
                    response_text = ""
                if response_text:
                    response_id, status, message = parse_response(
                        response_text
                    )
                    if response_id == command_id:
                        try:
                            self.response_path.unlink(missing_ok=True)
                        except OSError:
                            pass
                        if status == "ERROR":
                            raise InjectedBridgeError(
                                message
                                or (
                                    "Balatro rejected the injected bridge "
                                    "command"
                                )
                            )
                        return message

            if time.monotonic() >= deadline:
                raise InjectedBridgeTimeoutError(
                    "timed out waiting for the first-party Balatro bridge; "
                    "install the bridge and restart Balatro"
                )
            if self.poll_interval:
                time.sleep(self.poll_interval)
