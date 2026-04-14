from cogniaudit.demo_offline import DEMO_DRIFT_USER_INDICES, build_offline_demo_bundle


def test_offline_demo_bundle_shape() -> None:
    b = build_offline_demo_bundle()
    n_user = len([m for m in b.messages if m.role == "user"])
    assert n_user == b.next_user_index
    assert len(b.audit_history) == len(DEMO_DRIFT_USER_INDICES)
    for i, ui in enumerate(sorted(DEMO_DRIFT_USER_INDICES)):
        assert b.messages[ui * 2].role == "user"
        assert b.messages[ui * 2].user_index == ui
        assert b.audit_history[i]["status"] in {"ok", "no_meaningful_shift", "processing_error"}
