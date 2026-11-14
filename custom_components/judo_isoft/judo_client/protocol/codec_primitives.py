"""Protocol codec primitives for Judo command payloads."""

from __future__ import annotations

from datetime import datetime, timezone


def ensure_bytes_from_hex(hex_payload: str) -> bytes:
    """Parse hex payload into bytes."""
    clean = (hex_payload or "").strip()
    if clean.startswith("0x"):
        clean = clean[2:]
    return bytes.fromhex(clean)


def u8(data: bytes, offset: int = 0) -> int:
    """Decode unsigned 8-bit integer."""
    return data[offset]


def u16le(data: bytes, offset: int = 0) -> int:
    """Decode unsigned 16-bit little-endian integer."""
    return int.from_bytes(data[offset : offset + 2], byteorder="little", signed=False)


def i16le(data: bytes, offset: int = 0) -> int:
    """Decode signed 16-bit little-endian integer."""
    return int.from_bytes(data[offset : offset + 2], byteorder="little", signed=True)


def u24le(data: bytes, offset: int = 0) -> int:
    """Decode unsigned 24-bit little-endian integer."""
    return int.from_bytes(data[offset : offset + 3], byteorder="little", signed=False)


def u32le(data: bytes, offset: int = 0) -> int:
    """Decode unsigned 32-bit little-endian integer."""
    return int.from_bytes(data[offset : offset + 4], byteorder="little", signed=False)


def ascii_string(data: bytes) -> str:
    """Decode ASCII bytes and strip null/space padding."""
    return data.decode("ascii", errors="ignore").strip("\x00 ")


def unix_ts_from_u32le(data: bytes, offset: int = 0) -> str:
    """Decode unix timestamp (little-endian u32) into ISO string."""
    ts = u32le(data, offset)
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def bitmask(value: int, mapping: dict[int, str]) -> dict[str, bool]:
    """Decode a bitmask integer into named flags."""
    return {name: bool(value & bit) for bit, name in mapping.items()}


def encode_u8(value: int) -> str:
    """Encode unsigned 8-bit integer as uppercase hex."""
    if not 0 <= int(value) <= 0xFF:
        raise ValueError("Value out of range for u8")
    return f"{int(value):02X}"


def encode_u16le(value: int) -> str:
    """Encode unsigned 16-bit little-endian integer as uppercase hex."""
    if not 0 <= int(value) <= 0xFFFF:
        raise ValueError("Value out of range for u16")
    return int(value).to_bytes(2, byteorder="little", signed=False).hex().upper()


def encode_u32le(value: int) -> str:
    """Encode unsigned 32-bit little-endian integer as uppercase hex."""
    if not 0 <= int(value) <= 0xFFFFFFFF:
        raise ValueError("Value out of range for u32")
    return int(value).to_bytes(4, byteorder="little", signed=False).hex().upper()


def encode_ascii_fixed(value: str, length: int) -> str:
    """Encode ASCII value as fixed-size padded payload."""
    if length <= 0:
        raise ValueError("Length must be positive")
    payload = value.encode("ascii", errors="ignore")[:length]
    payload = payload.ljust(length, b"\x00")
    return payload.hex().upper()
