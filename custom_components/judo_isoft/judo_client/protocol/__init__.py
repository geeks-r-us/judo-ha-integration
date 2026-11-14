"""Protocol package for command catalog/decoding."""

from .catalog import infer_family, normalize_command_id
from .decoder import DecoderRegistry

__all__ = ["DecoderRegistry", "infer_family", "normalize_command_id"]
