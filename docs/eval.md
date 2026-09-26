# Evaluation Methodology — SafeSite AI

## Metrics used

- **IoU (Intersection over Union):** overlap between a predicted box and the ground-truth box. A prediction only counts as a correct detection (TP) if IoU ≥ threshold.
- **Precision:** TP / (TP + FP) — of everything we flagged, how much was real.
- **Recall:** TP / (TP + FN) — of everything real, how much we caught.
- **AP (Average Precision):** area under the precision-recall curve for one class, computed by ranking all predictions by confidence and sweeping the threshold.
- **mAP@50:** mean AP across all classes, at IoU threshold 0.5 (loose box-fit requirement).
- **mAP@50-95:** mean AP averaged across IoU thresholds 0.5 to 0.95, step 0.05 — a stricter, box-tightness-sensitive score.

## Why recall matters more than precision here

This is a safety system. A false positive (false alarm) costs a few seconds of a human's attention. A false negative (missed real violation) means a worker got hurt and nobody was warned. The cost of these two error types is not symmetric, so recall is prioritized over precision when tuning the confidence threshold — we'd rather over-flag than under-flag.

## Why mAP alone is not enough

mAP is a class-averaged number and can hide a badly-performing class behind others that perform well. Every evaluation reports **per-class AP and per-class recall**, not just the aggregate mAP, with particular attention to whichever class has the lowest recall — that is the class most likely to let a real violation through undetected.

## Data split plan

- **Train:** 70% — used to fit model weights.
- **Validation:** 15% — used during training to pick the best checkpoint and tune the confidence threshold, never used to update weights.
- **Test:** 15% — touched only once, at the end, to report the final numbers. Never used for any decision during development.
- Splits are done by *source video/clip*, not by individual frame, to avoid near-duplicate frames from the same clip leaking across splits and inflating scores.

## Target

- mAP@50 ≥ 0.75 across all classes on the test set.
- No individual class recall below 0.70 on the test set — this is the binding constraint, not the mAP average.

## Evaluation protocol

1. Run the trained model on the test set only, once.
2. Report mAP@50, mAP@50-95, and a per-class table of precision/recall/AP.
3. Inspect the confusion matrix for cross-class confusion (e.g., vest misclassified as no-vest).
4. Manually review a sample of false negatives to check for systematic causes (lighting, occlusion, distance) before concluding the model is "done."
