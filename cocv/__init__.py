"""Chain of Custody Verification (CoCV).

A cross-layer verification methodology for consumer privacy and security
software. Detects silent protection failures: cases where software reports
that a protective operation succeeded while it did not complete.
"""

from .chain import Chain, Handoff, Layer, VERIFICATION_POINTS
from .observation import Observation
from .reconcile import ChainResult, Divergence, reconcile
from .report import to_dict, to_json, to_text

__version__ = "0.1.1"
__all__ = [
    "Chain", "Handoff", "Layer", "VERIFICATION_POINTS",
    "Observation", "ChainResult", "Divergence", "reconcile",
    "to_dict", "to_json", "to_text",
]
