# Failure Cases — Day 9, Pretrained yolov8n on test_video.mp4

## Case 1 — NMS near-miss (duplicate box)
File: case1_nms_duplicate.png
Two overlapping "person" boxes drawn for the same worker (labels rendered as "persperson").
Likely cause: the two candidate boxes' IoU is high but fell just under NMS's suppression threshold, so both survived instead of being collapsed into one.

## Case 2 — False negative, missed worker on scaffolding
File: case2_missed_scaffold_worker.png
A visibly present worker near the top of frame, standing on scaffolding, received no bounding box at all.
Likely cause: small apparent size (far from camera) combined with partial occlusion by scaffold bars.

## Case 3 — False positive, misclassified object
File: case3_sportsball_fp.png
An object in a worker's hand (likely a tool or tied rebar) was classified as "sports ball" (conf 0.57).
Likely cause: COCO has no construction-tool class; the model mapped an unfamiliar shape to its closest known category. Direct evidence of the transfer-learning class gap discussed in Day 8.
