"""Decode protobuf messages using the client's protobufjs Liqi JSON schema."""

import base64
import json
import struct
from pathlib import Path

from games.mahjong_soul.live.external.liqi import _varint, fields


class LiqiSchema:
    def __init__(self, document):
        self.types = {}
        self.methods = {}

        def walk(node, prefix=""):
            for name, definition in node.get("nested", {}).items():
                qualified = f"{prefix}.{name}".strip(".")
                if "fields" in definition or "values" in definition:
                    self.types[qualified] = definition
                for method, route in definition.get("methods", {}).items():
                    self.methods[f".{qualified}.{method}"] = (
                        self.resolve_name(route["requestType"], qualified),
                        self.resolve_name(route["responseType"], qualified))
                walk(definition, qualified)

        # Resolve RPC names after all message definitions have been indexed.
        self.document = document
        walk(document)
        for method, pair in list(self.methods.items()):
            context = method.strip(".").rsplit(".", 1)[0]
            self.methods[method] = tuple(self.resolve_name(name, context) for name in pair)

    @classmethod
    def load(cls, path):
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def resolve_name(self, name, context):
        name = name.lstrip(".")
        if name in self.types:
            return name
        parts = context.split(".")
        while parts:
            candidate = ".".join(parts + [name])
            if candidate in self.types:
                return candidate
            parts.pop()
        return name

    def decode(self, name, data, depth=0):
        if depth > 32:
            raise ValueError("Message nesting exceeds limit")
        name = name.lstrip(".")
        definition = self.types.get(name)
        if definition is None or "fields" not in definition:
            raise ValueError(f"Unknown message type: {name}")
        wire_fields = fields(data)
        result = {}
        for field_name, spec in definition["fields"].items():
            repeated = spec.get("rule") == "repeated"
            field_type = self.resolve_name(spec["type"], name)
            entries = wire_fields.get(spec["id"], [])
            if entries and "keyType" in spec:
                raise ValueError("Map fields are not supported yet")
            values = []
            for wire, value in entries:
                if repeated and wire == 2 and self._numeric(field_type):
                    offset = 0
                    scalar_wire = 1 if field_type in ("double", "fixed64", "sfixed64") else 5 if field_type in ("float", "fixed32", "sfixed32") else 0
                    while offset < len(value):
                        if scalar_wire == 0:
                            item, offset = _varint(value, offset)
                        else:
                            size = 8 if scalar_wire == 1 else 4
                            item = value[offset:offset + size]
                            if len(item) != size:
                                raise ValueError("Truncated packed field")
                            offset += size
                        values.append(self._field_value(field_type, scalar_wire, item, depth, name + "." + field_name))
                else:
                    values.append(self._field_value(field_type, wire, value, depth, name + "." + field_name))
            if repeated:
                result[field_name] = values
            elif values:
                result[field_name] = values[-1]
            elif field_type == "string":
                result[field_name] = ""
            elif field_type == "bytes":
                result[field_name] = ""
            elif self._numeric(field_type):
                result[field_name] = False if field_type == "bool" else 0
            # Absent message fields remain absent, preserving presence semantics.
        return result

    def _field_value(self, name, wire, value, depth, location):
        try:
            return self._scalar(name, wire, value, depth)
        except (ValueError, UnicodeError, struct.error) as error:
            raise ValueError(f"{location}: {error}") from error

    def _numeric(self, name):
        return name in {"int32", "int64", "uint32", "uint64", "sint32", "sint64", "bool",
                        "fixed32", "fixed64", "sfixed32", "sfixed64", "float", "double"} or "values" in self.types.get(name, {})

    def _scalar(self, name, wire, value, depth):
        if name in ("string", "bytes") or "fields" in self.types.get(name, {}):
            if wire != 2:
                raise ValueError(f"Wrong wire type for {name}")
            if name == "string":
                return value.decode("utf-8")
            if name == "bytes":
                return base64.b64encode(value).decode("ascii")
            return self.decode(name, value, depth + 1)
        formats = {"double": (1, "<d"), "float": (5, "<f"),
                   "fixed64": (1, "<Q"), "sfixed64": (1, "<q"),
                   "fixed32": (5, "<I"), "sfixed32": (5, "<i")}
        if name in formats:
            expected, fmt = formats[name]
            if wire != expected:
                raise ValueError(f"Wrong wire type for {name}")
            return struct.unpack(fmt, value)[0]
        if not self._numeric(name) or wire != 0:
            raise ValueError(f"Unsupported field type or wire: {name}/{wire}")
        if name == "bool":
            return bool(value)
        if name.startswith("sint"):
            return (value >> 1) ^ -(value & 1)
        if name in ("int32", "int64"):
            bits = 32 if name == "int32" else 64
            value &= (1 << bits) - 1
            if value & (1 << (bits - 1)):
                value -= 1 << bits
        return value
