from src.episodes import detect_episodes


def test_short_track_is_filtered_out():
    # Only 3 frames, below MIN_TRACK_FRAMES (5) - should be dropped as noise,
    # even though every frame says violation.
    detections = [(0, "t1", "NO-Hardhat"), (1, "t1", "NO-Hardhat"), (2, "t1", "NO-Hardhat")]
    assert detect_episodes(detections) == []


def test_exact_tie_flags_violation():
    # 6 frames, 3 compliant / 3 violation - exact 0.5 tie, should resolve
    # in favor of flagging (recall-priority decision).
    detections = [
        (0, "t1", None), (1, "t1", "NO-Safety Vest"),
        (2, "t1", None), (3, "t1", "NO-Safety Vest"),
        (4, "t1", None), (5, "t1", "NO-Safety Vest"),
    ]
    episodes = detect_episodes(detections)
    assert len(episodes) == 1
    assert episodes[0]["violation_type"] == "NO-Safety Vest"
    assert episodes[0]["majority_fraction"] == 0.5


def test_clear_majority_violation():
    detections = [(i, "t1", "NO-Hardhat") for i in range(8)] + [(8, "t1", None), (9, "t1", None)]
    episodes = detect_episodes(detections)
    assert len(episodes) == 1
    assert episodes[0]["violation_type"] == "NO-Hardhat"
    assert episodes[0]["frame_count"] == 10
    assert episodes[0]["majority_fraction"] == 0.8


def test_majority_compliant_suppresses_episode():
    # Violation appears, but compliant frames clearly dominate (0.3 < 0.5) - no episode.
    detections = [(i, "t1", None) for i in range(7)] + [(7, "t1", "NO-Mask"), (8, "t1", "NO-Mask"), (9, "t1", "NO-Mask")]
    assert detect_episodes(detections) == []


def test_no_violation_ever_produces_no_episode():
    detections = [(i, "t1", None) for i in range(6)]
    assert detect_episodes(detections) == []


def test_two_violation_types_picks_the_dominant_one():
    detections = [(i, "t1", "NO-Hardhat") for i in range(4)] + [(4, "t1", "NO-Mask"), (5, "t1", "NO-Mask")]
    episodes = detect_episodes(detections)
    assert len(episodes) == 1
    assert episodes[0]["violation_type"] == "NO-Hardhat"


def test_multiple_tracks_are_independent():
    detections = [
        (0, "t1", "NO-Hardhat"), (1, "t1", "NO-Hardhat"), (2, "t1", "NO-Hardhat"),
        (3, "t1", "NO-Hardhat"), (4, "t1", "NO-Hardhat"),
        (0, "t2", None), (1, "t2", None), (2, "t2", None), (3, "t2", None), (4, "t2", None),
    ]
    episodes = detect_episodes(detections)
    assert len(episodes) == 1
    assert episodes[0]["track_id"] == "t1"
