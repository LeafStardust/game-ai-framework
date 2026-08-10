import json
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from games.balatro.actions import (
    BUY_CONSUMABLE,
    BUY_JOKER,
    BUY_VOUCHER,
    DISCARD_CARDS,
    END_ROUND,
    END_SHOP,
    PLAY_CARDS,
    REFRESH_SHOP,
    SELL_JOKER,
    USE_CONSUMABLE,
)
from games.balatro.live.interfaces import BalatroLiveBridge
from games.balatro.live.protocol import (
    LiveBalatroCommand,
    LiveBalatroSnapshot,
)


class BalatroBotError(RuntimeError):
    pass


class BalatroBotConnectionError(BalatroBotError):
    pass


class BalatroBotRpcError(BalatroBotError):

    def __init__(
        self,
        code: int,
        message: str,
        data: dict | None = None,
    ):
        self.code = code
        self.data = data or {}
        super().__init__(message)


class BalatroBotBridge(BalatroLiveBridge):
    """BalatroBot JSON-RPC backend for the live Balatro integration."""

    DEFAULT_ENDPOINT = "http://127.0.0.1:12346"

    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        timeout: float = 5.0,
        requester: Callable[[str, dict, float], dict] | None = None,
    ):
        self.endpoint = endpoint
        self.timeout = timeout
        self.requester = requester or self._http_request
        self._request_id = 0
        self._sequence = 0
        self._last_fingerprint: str | None = None
        self._pending_result: dict | None = None

    def observe(self) -> LiveBalatroSnapshot:
        if self._pending_result is not None:
            result = self._pending_result
            self._pending_result = None
        else:
            result = self.call("gamestate")

        if not isinstance(result, dict):
            raise BalatroBotError("BalatroBot gamestate did not return an object")

        return self._snapshot(result)

    def send(self, command: LiveBalatroCommand) -> None:
        method, params = self._rpc_action(command)
        result = self.call(method, params)

        if isinstance(result, dict) and "state" in result:
            self._pending_result = result

    def request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> LiveBalatroSnapshot:
        result = self.call(method, params)

        if not isinstance(result, dict) or "state" not in result:
            raise BalatroBotError(
                f"BalatroBot {method} did not return game state"
            )

        self._pending_result = None
        return self._snapshot(result)

    def is_connected(self) -> bool:
        try:
            result = self.call("health")
        except BalatroBotError:
            return False

        return isinstance(result, dict) and result.get("status") == "ok"

    def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": self._request_id,
        }

        if params:
            request["params"] = params

        response = self.requester(
            self.endpoint,
            request,
            self.timeout,
        )

        if not isinstance(response, dict):
            raise BalatroBotError("invalid BalatroBot JSON-RPC response")

        error = response.get("error")
        if error:
            raise BalatroBotRpcError(
                int(error.get("code", -32000)),
                str(error.get("message", "BalatroBot RPC error")),
                error.get("data"),
            )

        return response.get("result")

    def _snapshot(self, result: dict) -> LiveBalatroSnapshot:
        fingerprint = json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
        )

        if fingerprint != self._last_fingerprint:
            self._sequence += 1
            self._last_fingerprint = fingerprint

        return LiveBalatroSnapshot(
            sequence=self._sequence,
            phase=str(result.get("state", "UNKNOWN")),
            state_complete=True,
            payload=result,
        )

    def _rpc_action(
        self,
        command: LiveBalatroCommand,
    ) -> tuple[str, dict]:
        payload = command.payload

        if command.action == PLAY_CARDS:
            return "play", {
                "cards": self._indices(payload.get("cards", []))
            }

        if command.action == DISCARD_CARDS:
            return "discard", {
                "cards": self._indices(payload.get("cards", []))
            }

        if command.action in {BUY_JOKER, BUY_CONSUMABLE}:
            return "buy", {
                "card": self._index(payload.get("target"))
            }

        if command.action == BUY_VOUCHER:
            return "buy", {
                "voucher": self._index(payload.get("target"))
            }

        if command.action == SELL_JOKER:
            return "sell", {
                "joker": self._index(payload.get("target"))
            }

        if command.action == REFRESH_SHOP:
            return "reroll", {}

        if command.action == END_SHOP:
            return "next_round", {}

        if command.action == END_ROUND:
            return "cash_out", {}

        if command.action == USE_CONSUMABLE:
            params = {
                "consumable": self._index(payload.get("target"))
            }
            cards = payload.get("cards", [])
            if cards:
                params["cards"] = self._indices(cards)
            return "use", params

        raise ValueError(
            f"unsupported live Balatro action: {command.action}"
        )

    @staticmethod
    def _index(value) -> int:
        if value is None:
            raise ValueError("BalatroBot action target is required")
        return int(value)

    @classmethod
    def _indices(cls, values: list) -> list[int]:
        return [cls._index(value) for value in values]

    @staticmethod
    def _http_request(
        endpoint: str,
        payload: dict,
        timeout: float,
    ) -> dict:
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(
                    response.read().decode("utf-8")
                )
        except (HTTPError, URLError, OSError) as error:
            raise BalatroBotConnectionError(
                f"unable to reach BalatroBot at {endpoint}"
            ) from error
        except json.JSONDecodeError as error:
            raise BalatroBotError(
                "BalatroBot returned invalid JSON"
            ) from error
