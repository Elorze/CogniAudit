import numpy as np

from cogniaudit.drift import SignalState, cosine_distance


def test_cosine_distance_basic() -> None:
    a = np.array([1.0, 0.0])
    b = np.array([1.0, 0.0])
    c = np.array([0.0, 1.0])
    assert cosine_distance(a, b) == 0.0
    assert abs(cosine_distance(a, c) - 1.0) < 1e-9


def test_signal_state_anchor_and_window() -> None:
    s = SignalState(k=3, delta=0.02)
    out0 = s.ingest_user_vector([1.0, 0.0])
    out1 = s.ingest_user_vector([1.0, 0.0])
    out2 = s.ingest_user_vector([1.0, 0.0])
    assert out0["ready"] is False
    assert out1["ready"] is False
    assert out2["ready"] is True
    assert s.v_anchor is not None
    assert out2["d_t"] == 0.0


def test_signal_state_can_detect_drift_eventually() -> None:
    # Not asserting exact timing (ADWIN is statistical),
    # but we should eventually drift if distances stay high.
    s = SignalState(k=3, delta=0.02)
    # stable phase
    for _ in range(20):
        s.ingest_user_vector([1.0, 0.0])
    # shift phase: orthogonal vectors -> high cosine distance
    drift_seen = False
    for _ in range(400):
        out = s.ingest_user_vector([0.0, 1.0])
        if out["drift_detected"]:
            drift_seen = True
            break
    assert drift_seen

