from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from river.drift import ADWIN


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1.0
    return float(1.0 - float(np.dot(a, b)) / denom)


@dataclass
class SignalState:
    """
    Implements Final Spec:
    - k=3 user embedding window mean: V_window
    - anchor: mean of first 3 user embeddings, then reset to V_window when drift detected
    - scalar stream: d_t = 1 - cos(V_anchor, V_window)
    """

    k: int = 3
    delta: float = 0.02
    adwin: ADWIN = field(default_factory=lambda: ADWIN(delta=0.02))
    user_vectors: list[np.ndarray] = field(default_factory=list)

    v_anchor: Optional[np.ndarray] = None
    last_d_t: Optional[float] = None

    def reset(self) -> None:
        self.adwin = ADWIN(delta=self.delta)
        self.user_vectors.clear()
        self.v_anchor = None
        self.last_d_t = None

    def ingest_user_vector(self, vec: list[float]) -> dict:
        """
        Ingest a new user embedding vector.

        Returns a dict with:
        - user_index: index of this user message (0-based)
        - ready: whether we have enough vectors to compute window mean
        - d_t: computed scalar (or None)
        - drift_detected: boolean
        """
        v = np.asarray(vec, dtype=np.float64)
        self.user_vectors.append(v)
        user_index = len(self.user_vectors) - 1

        if len(self.user_vectors) < self.k:
            return {
                "user_index": user_index,
                "ready": False,
                "d_t": None,
                "drift_detected": False,
            }

        # window mean of last k vectors
        window = self.user_vectors[-self.k :]
        v_window = np.mean(window, axis=0)

        # initialize anchor with mean of first k user vectors
        if self.v_anchor is None and len(self.user_vectors) >= self.k:
            self.v_anchor = np.mean(self.user_vectors[: self.k], axis=0)

        assert self.v_anchor is not None
        d_t = cosine_distance(self.v_anchor, v_window)
        self.last_d_t = d_t

        self.adwin.update(d_t)
        drift = bool(self.adwin.drift_detected)

        drift_event = False
        if drift:
            drift_event = True
            # Reset anchor to window mean (rolling cognitive stages)
            self.v_anchor = v_window
            # ADWIN may keep drift_detected latched; for demo we restart the detector
            # after each event so subsequent drifts remain detectable.
            self.adwin = ADWIN(delta=self.delta)

        return {
            "user_index": user_index,
            "ready": True,
            "d_t": d_t,
            "drift_detected": drift_event,
        }

