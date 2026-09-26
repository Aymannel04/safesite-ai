"""
Episode detection: converts a raw stream of per-frame (track_id, label)
detections into deduplicated violation episodes.

Design decisions:
- MIN_TRACK_FRAMES = 5: an intuition-based heuristic, not derived from
  labeled data. At ~30fps this is roughly 167ms, chosen to filter out
  single-frame detection noise (see failure_cases/log.md, Day 9) without
  discarding genuinely brief real violations. Should be re-tuned once
  labeled ground-truth episode data is available (docs/eval.md's
  "measure, don't assume" principle).
- MAJORITY_THRESHOLD = 0.5, ties resolved in favor of flagging a
  violation: per docs/eval.md, recall is prioritized over precision for
  this safety system. Day 12's tracking observations
  (docs/tracking_observations.md) showed real per-frame label flicker on
  small/distant/occluded subjects, so a strict supermajority requirement
  would systematically miss real violations on exactly the highest-risk
  population. A violation type needs only to be at least as common as
  compliant frames within a track's lifetime to register as one episode.
"""

from collections import Counter, defaultdict

MIN_TRACK_FRAMES = 5
MAJORITY_THRESHOLD = 0.5


def detect_episodes(detections, min_frames=MIN_TRACK_FRAMES, majority_threshold=MAJORITY_THRESHOLD):
    """
    detections: list of (frame_idx, track_id, label) tuples.
        label is a violation class name (e.g. "NO-Hardhat") or None (compliant).

    Returns: list of episode dicts:
        {track_id, violation_type, start_frame, end_frame, frame_count, majority_fraction}
    """
    tracks = defaultdict(list)
    for frame_idx, track_id, label in detections:
        tracks[track_id].append((frame_idx, label))

    episodes = []
    for track_id, frames in tracks.items():
        frames.sort(key=lambda x: x[0])
        frame_count = len(frames)
        if frame_count < min_frames:
            continue

        violation_labels = [label for _, label in frames if label is not None]
        if not violation_labels:
            continue

        top_label, top_count = Counter(violation_labels).most_common(1)[0]
        majority_fraction = top_count / frame_count

        if majority_fraction >= majority_threshold:
            episodes.append({
                "track_id": track_id,
                "violation_type": top_label,
                "start_frame": frames[0][0],
                "end_frame": frames[-1][0],
                "frame_count": frame_count,
                "majority_fraction": round(majority_fraction, 3),
            })

    return episodes
