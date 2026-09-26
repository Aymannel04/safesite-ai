# Tracking Observations — Day 12, ByteTrack on yolov8s_ppe_v1

## Setup
- Model: models/yolov8s_ppe_v1.pt (Day 10-11 fine-tuned checkpoint)
- Video: data/samples/test_video.mp4
- Tracker: bytetrack.yaml (ultralytics default), via `yolo track`

## Observation 1 — Stable tracking on a close, unobstructed subject
The main worker closest to the camera kept a single consistent identity (Person id:43, Safety Vest id:51, Hardhat id:52) across the entire video, from early frames (alongside low IDs like id:1-3) through to the end (alongside high IDs like id:287-302). Confirms ByteTrack works as intended when the subject is large, clear, and continuously detected.

## Observation 2 — ID fragmentation on a distant/occluded subject
A single physical background worker (small, partially occluded, near the top of frame on scaffolding) was assigned at least 5 different track IDs over the course of the video: 238, 260, 262, 149, 281. Each time the detector's confidence dipped and the box dropped for even one frame, ByteTrack lost the track and created a new ID on reappearance rather than recognizing it as a continuation. Root cause: ByteTrack matches tracks using only motion + box overlap (IoU) between consecutive frames - it has no visual appearance model, so it cannot re-link a track across a gap. This directly connects to the Day 9 failure case of a missed distant/occluded worker: the same population (small, far, partially hidden) that is hardest to detect is also hardest to track continuously.

## Observation 3 — Classification flicker within the same fragmented identity
Across those same ID fragments (238, 260, 281...), the classification itself alternated between "Safety Vest" (compliant) and "NO-Safety Vest" (violation) for what is visibly the same person wearing the same vest throughout. Root cause: at small/distant scale, the model's confidence sits near the decision boundary between these two visually similar classes, so small per-frame variation (lighting, angle, motion blur) flips the predicted label.

## Implication for Day 13 episode logic
The original plan ("same track ID + same violation type, held for N consecutive frames = one episode") assumes stable IDs and stable per-frame labels. Both assumptions fail specifically for small/distant/occluded workers - exactly the population most at risk and hardest to protect. Two compounding failure modes stack on the same subjects:
1. ID fragmentation prevents any single track from accumulating N consecutive frames.
2. Label flicker prevents N *consecutive identical* labels even within one continuous track.

Decision: Day 13 episode logic will use majority-vote classification within a track's lifetime (e.g., a track is counted as a NO-Safety-Vest episode if that label appears in >60% of its frames) rather than requiring strict consecutive identical labels. This is more robust to the flicker observed here, though it does not solve ID fragmentation itself - that would require a re-identification-capable tracker (e.g., DeepSORT/StrongSORT with appearance embeddings), noted as a candidate future improvement, out of scope for now.
