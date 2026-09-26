# Fine-Tuning Results — yolov8s on PPE Dataset (v1)

## Setup
- Base model: yolov8s.pt (pretrained on COCO)
- Dataset: Roboflow "Construction Site Safety" v27, 2801 images (2603 train / 114 val / test split), 10 classes
- Training: 50 epochs, imgsz=640, batch=16, GPU: RTX 4060 Laptop (8GB VRAM)
- Training time: 21.5 minutes
- Checkpoint saved: models/yolov8s_ppe_v1.pt

## Headline metrics
- mAP@50: 0.810 (target from docs/eval.md: ≥0.75 — MET)
- Precision: 0.918
- Recall: 0.759
- Reference point: Roboflow's own published model on this dataset achieves mAP@50 0.841, precision 0.927, recall 0.774 — this run lands close to that benchmark, suggesting the training pipeline itself is sound.

## Per-class breakdown

| Class          | Images | Instances | Precision | Recall | mAP50 | mAP50-95 |
|----------------|--------|-----------|-----------|--------|-------|----------|
| Hardhat        | 42     | 79        | 0.938     | 0.765  | 0.812 | 0.524    |
| Mask           | 19     | 21        | 1.000     | 0.901  | 0.905 | 0.722    |
| NO-Hardhat     | 37     | 69        | 0.900     | 0.609  | 0.704 | 0.401    |
| NO-Mask        | 44     | 74        | 0.925     | 0.689  | 0.744 | 0.397    |
| NO-Safety Vest | 56     | 106       | 0.890     | 0.670  | 0.752 | 0.462    |
| Person         | 84     | 166       | 0.907     | 0.807  | 0.840 | 0.538    |
| Safety Cone    | 13     | 44        | 0.972     | 0.864  | 0.915 | 0.546    |
| Safety Vest    | 28     | 41        | 0.941     | 0.778  | 0.876 | 0.615    |
| machinery      | 26     | 55        | 0.897     | 0.891  | 0.923 | 0.673    |
| vehicle        | 16     | 42        | 0.812     | 0.619  | 0.634 | -        |

## Binding constraint check (per docs/eval.md: no class recall below 0.70)

FAILS the binding constraint. Four classes fall below the 0.70 recall floor:
- NO-Hardhat: 0.609
- NO-Mask: 0.689
- NO-Safety Vest: 0.670
- vehicle: 0.619

## Key finding

The aggregate mAP@50 (0.810) clears the target and looks strong in isolation — this is precisely the failure mode docs/eval.md was written to guard against. Per-class inspection reveals the model is meaningfully weaker on the "NO-*" (violation) classes than on the "presence" classes (Hardhat, Safety Vest, Mask, Person). This is the worst possible place for weakness in a safety system: these are exactly the classes responsible for catching real violations. A model evaluated only on aggregate mAP would have been shipped without this gap ever being noticed.

Likely contributing factor: `vehicle` also has the fewest validation instances (16 images, 42 instances) of any class, suggesting limited training data for that class as a partial explanation. The NO-* classes have comparable image/instance counts to their positive counterparts (e.g., NO-Hardhat: 37 images/69 instances vs Hardhat: 42/79), so data volume alone does not fully explain their gap — the negative/absence concept appears to be intrinsically harder for the model to learn than object presence.

## Decision

Documented as a known limitation of v1. Proceeding to Day 12 (tracking) with this checkpoint rather than iterating further on recall at this stage, per the project's fallback principle (log the decision, move forward, revisit if time allows). Candidate future improvements: targeted data augmentation for NO-* classes, class-weighted loss, or additional labeled examples for vehicle.
