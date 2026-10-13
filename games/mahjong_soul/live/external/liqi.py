"""Schema-independent Liqi envelope inspection; payloads remain opaque."""

import base64


def _varint(data, offset):
    value = 0
    for shift in range(0, 70, 7):
        if offset >= len(data):
            raise ValueError("Truncated varint")
        byte = data[offset]
        offset += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, offset
    raise ValueError("Oversized varint")


def fields(data):
    """Read protobuf wire fields without guessing their schema."""
    result = {}
    offset = 0
    while offset < len(data):
        tag, offset = _varint(data, offset)
        number, wire = tag >> 3, tag & 7
        if number == 0:
            raise ValueError("Invalid protobuf field")
        if wire == 0:
            value, offset = _varint(data, offset)
        elif wire in (1, 2, 5):
            if wire == 2:
                size, offset = _varint(data, offset)
            else:
                size = 8 if wire == 1 else 4
            end = offset + size
            if end > len(data):
                raise ValueError("Truncated protobuf field")
            value = data[offset:end]
            offset = end
        else:
            raise ValueError(f"Unsupported protobuf wire type {wire}")
        result.setdefault(number, []).append((wire, value))
    return result


def _last(values, number, wire, default):
    entries = values.get(number, [])
    if not entries:
        return default
    actual_wire, value = entries[-1]
    if actual_wire != wire:
        raise ValueError(f"Unexpected wire type for field {number}")
    return value


def decode_envelope(data):
    """Decode notification/request/response framing and action metadata."""
    if not data or data[0] not in (1, 2, 3):
        raise ValueError("Not a supported Liqi frame")
    kind = data[0]
    offset = 1 if kind == 1 else 3
    if len(data) < offset:
        raise ValueError("Truncated Liqi header")
    wrapper = fields(data[offset:])
    method = _last(wrapper, 1, 2, b"").decode("utf-8")
    payload = _last(wrapper, 2, 2, b"")
    result = {
        "kind": {1: "notification", 2: "request", 3: "response"}[kind],
        "request_id": None if kind == 1 else int.from_bytes(data[1:3], "little"),
        "method": method,
        "payload_base64": base64.b64encode(payload).decode("ascii"),
    }
    if method == ".lq.ActionPrototype":
        action = fields(payload)
        result["action"] = _last(action, 2, 2, b"").decode("utf-8")
        result["step"] = _last(action, 1, 0, 0)
        # Inner action bytes may be obfuscated; do not guess tile values here.
    return result
