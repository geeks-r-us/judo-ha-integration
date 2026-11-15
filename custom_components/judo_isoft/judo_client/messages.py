"""Judo device messages (event log) from the cloud `get error messages` command."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

JUDO_TZ = ZoneInfo("Europe/Berlin")

# Message type "w" (warning/notice) and "e" (error), keyed as "<type>_<code>".
MESSAGE_TEXTS: dict[str, str] = {
    "w_20": "Leakage protection closed",
    "w_21": "Leakage protection closed: max. draw volume exceeded",
    "w_22": "Leakage protection closed: max. draw duration exceeded",
    "w_23": "Leakage protection closed: max. flow exceeded",
    "w_24": "Leak sensor reports a leak",
    "w_26": "Leakage protection in sleep mode",
    "w_27": "Maintenance due",
    "w_28": "Check salt supply",
    "w_29": "Salt shortage",
    "w_30": "Regeneration running",
    "w_31": "Battery low",
    "w_32": "Battery empty",
    "w_40": "Fault: regeneration drive defective",
    "w_41": "Fault: brine level too high",
    "w_42": "Fault: filling valve malfunction",
    "w_43": "Fault: leakage protection defective",
    "w_46": "Leakage protection in special mode",
    "w_51": "Leakage protection: max. draw volume exceeded",
    "w_52": "Leakage protection: max. draw duration exceeded",
    "w_53": "Leakage protection: max. flow exceeded",
    "w_61": "Filling valve closed: max. filling time exceeded",
    "w_62": "Filling valve closed: max. filling volume exceeded",
    "w_63": "Filling valve closed: max. filling cycles exceeded",
    "w_64": "Cartridge used up",
    "w_65": "Fault: pressure sensor defective",
    "w_66": "Fault: home position",
    "w_67": "Fault: keypad defective",
    "w_68": "Fault: valve leaking",
    "w_69": "Leakage protection in sleep mode",
    "w_70": "Leakage protection closed: floor sensor reports a leak",
    "w_71": "Learning mode: closed, max. draw volume exceeded",
    "w_72": "Learning mode: closed, max. flow exceeded",
    "w_73": "Learning mode: closed, max. draw duration exceeded",
    "w_74": "Fault: ball valve defective",
    "w_151": "Leak alarm: max. draw volume exceeded",
    "w_152": "Leak alarm: max. draw duration exceeded",
    "w_153": "Leak alarm: max. flow exceeded",
    "w_251": "Vacation mode: reduced limits",
    "w_253": "Vacation mode: leakage protection closed",
    "e_1": "Error: regeneration drive",
    "e_2": "Error: brine level high",
    "e_3": "Error: refilling",
    "e_4": "Error: water stop drive",
    "e_5": "Error: VSV",
    "e_6": "Error: conductivity measurement",
    "e_7": "Error: temperature measurement",
    "e_8": "Error: soft water meter",
    "e_9": "Error: raw water meter",
    "e_10": "Error: raw hardness below twice the target",
    "e_11": "Error: level sensor not detected",
    "e_12": "Error: upper level sensor always wet",
    "e_13": "Error: level sensors (double fault)",
    "e_14": "Error: RS-485 connection",
}


def describe_message(msg_type: str, code: Any) -> str:
    """Return a human readable text for a message type and code."""
    key = f"{msg_type}_{code}"
    return MESSAGE_TEXTS.get(key, f"Unknown message ({key})")


def _to_utc_iso(value: Any) -> str | None:
    """Convert the cloud's German local time (no offset) to a UTC ISO string."""
    text = str(value or "").strip().split(".")[0]
    try:
        local = datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=JUDO_TZ)
    except ValueError:
        return None
    return local.astimezone(timezone.utc).isoformat()


def parse_messages(payload: dict[str, Any], serial: str | None = None) -> list[dict[str, Any]]:
    """Normalize a `get error messages` answer, newest first."""
    entries = payload.get("data")
    if not isinstance(entries, list):
        return []

    messages: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if serial and str(entry.get("serialnumber") or "") != str(serial):
            continue
        msg_type = str(entry.get("type") or "")
        code = entry.get("error")
        try:
            message_id = int(entry.get("id", 0))
        except (TypeError, ValueError):
            message_id = 0
        messages.append(
            {
                "id": message_id,
                "type": msg_type,
                "code": code,
                "text": describe_message(msg_type, code),
                "timestamp": _to_utc_iso(entry.get("ts_sort")),
                "confirmed": entry.get("confirm_status") not in (0, "0", None),
                "param": entry.get("param") or None,
            }
        )
    messages.sort(key=lambda m: (m["timestamp"] or "", m["id"]), reverse=True)
    return messages
