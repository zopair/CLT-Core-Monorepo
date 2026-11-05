"""Application envelope and replay-window primitives."""
from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Any


def make_envelope(payload: Any, sequence: int, nonce: str | None = None) -> dict:
    if not isinstance(sequence, int) or sequence < 0:
        raise ValueError("sequence must be a non-negative integer")
    return {
        "version": 1,
        "type": "data",
        "sequence": sequence,
        "nonce": nonce or secrets.token_hex(16),
        "payload": payload,
    }


@dataclass
class ReplayWindow:
    max_nonces: int = 4096
    last_sequence: int = -1
    _nonces: set[str] = field(default_factory=set)

    def accept(self, sequence: int, nonce: str) -> bool:
        if not isinstance(sequence, int) or sequence <= self.last_sequence:
            return False
        if not isinstance(nonce, str) or not nonce or nonce in self._nonces:
            return False
        self.last_sequence = sequence
        self._nonces.add(nonce)
        if len(self._nonces) > self.max_nonces:
            self._nonces = set(list(self._nonces)[-self.max_nonces :])
        return True
