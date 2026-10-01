Day 2: Git branching + merge conflict resolved, GitHub repo live (safesite-ai), venv + logging module built, first PR merged. Caught venv/__pycache__ before committing, added .gitignore.
Day 3: Docker Compose with Postgres + Adminer, volumes and networks understood and proven empirically (data survived a full container down/up cycle).
Day 4: Designed and built cameras/violations schema with constraints (proved CHECK and FK work by triggering real rejections). Seeded 5000 fake violations via psycopg2. Wrote 5 real dashboard queries (WHERE/ORDER BY/GROUP BY/JOIN/DATE_TRUNC). Learned indexes are a cost-based planner decision, not automatic - proved Seq Scan vs Index Scan directly with EXPLAIN ANALYZE.
Day 5: Built FastAPI app with GET /violations (query filters), POST /violations (Pydantic validation), GET /stats/daily. Proved Pydantic rejects invalid confidence with 422 before Postgres is ever touched - defense in depth alongside the CHECK constraint. Learned HTTP request/response model, status codes, and why JSON (not HTML) is the right format for machine-to-machine data.
Day 6: Wrote pytest integration tests (list, create valid, create invalid confidence rejected, filter) using FastAPI's TestClient - all passing. Froze Violation Event Contract v1 in docs/contracts.md, documenting the two-layer validation (Pydantic + Postgres CHECK) and a known limitation (FK violations currently return raw 500, to be fixed later). Learned unit vs integration tests and why schema contracts need semantic versioning once other services depend on them.
Day 7: Read video frame-by-frame with OpenCV, sampled 1 frame/sec, measured resolution cost (half-res was slower than full-res in isolation - resize overhead with no downstream work to offset it, a reminder that optimizations must be measured, not assumed, same lesson as Day 4's index surprise). Weekly review completed out loud - volumes, foreign keys, Pydantic vs CHECK constraint layering all confirmed solid.

## Day 8 — Detection theory
Learned classification vs detection, IoU (hand-computed two examples), precision/recall and why recall > precision for a safety system, NMS, mAP@50 vs mAP@50-95 and how a class-averaged score can hide a failing class, and why fine-tuning beats training from scratch (early CNN layers learn universal features like edges/shapes; only late layers are task-specific). Froze evaluation methodology in docs/eval.md: metrics, 70/15/15 split by source clip, mAP@50 ≥ 0.75 target with per-class recall ≥ 0.70 as the binding constraint.

## Day 9 — Pretrained YOLO on real footage
Installed ultralytics, confirmed GPU (RTX 4060) detected by torch/CUDA. Ran pretrained yolov8n on the Day 7 test video: inference ~8-17ms/frame (well within real-time). Confirmed the transfer-learning gap from Day 8 concretely - the model only ever output COCO classes (person, traffic light), never anything PPE-related, since those classes don't exist in COCO. Manually collected 3 failure cases into failure_cases/: an NMS near-miss (duplicate overlapping box on one person), a false negative (small/occluded worker on scaffolding missed entirely), and a false positive (a held tool misclassified as "sports ball"). Added runs/ and *.pt to .gitignore (regenerable model weights and inference output, same reasoning as data/).

## Days 10-11 — Fine-tuning yolov8s on PPE dataset
Downloaded Roboflow's "Construction Site Safety" dataset (2801 images, 10 classes) via the roboflow Python package, API key kept in .env. Fixed a data.yaml path bug (Roboflow's export used "../train/images" which pointed one directory too high). Hit a recurring WSL2 GPU driver crash (CUDA_ERROR_UNKNOWN) twice during training - root-caused to thermal/driver instability under sustained load rather than a config bug, fixed by restarting WSL and monitoring temperature (peaked 80-90C) during the successful run. Fine-tuned yolov8s for 50 epochs (21.5 min on the RTX 4060): mAP@50 = 0.81, beating the 0.75 target, but per-class inspection showed 4 classes (NO-Hardhat, NO-Mask, NO-Safety Vest, vehicle) fail the 0.70 recall floor defined in docs/eval.md - the exact mAP-hides-a-weak-class scenario from Day 8's theory, and worst of all on the violation classes the whole system exists to catch. Documented as a known limitation in docs/training_results_v1.md rather than over-iterating now. Learned to fix an overly broad .gitignore rule (*.pt was silently excluding the real trained checkpoint, not just re-downloadable base weights) with a targeted negation pattern.

## Day 12 — Tracking with ByteTrack
Ran yolo track with ByteTrack on the fine-tuned model. Confirmed stable tracking on the close/clear subject (same 3 IDs held for the whole video), but found real ID fragmentation on a distant/occluded background worker (5+ different IDs for the same person) plus classification flicker between Safety Vest and NO-Safety Vest for that same person across fragments. Root-caused both to the same underlying weakness: small/distant/occluded objects sit near the model's decision boundary (label flicker) and ByteTrack has no appearance model to re-link tracks across a gap (ID fragmentation) - directly connects to the Day 9 failure case of a missed distant worker. Documented in docs/tracking_observations.md. Decided Day 13's episode logic will use majority-vote classification within a track's lifetime rather than requiring strict consecutive-identical labels, since the flicker observed here would break that stricter approach for exactly the highest-risk workers.

## Day 13 — Episode detection logic
Designed and implemented src/episodes.py: converts a raw (frame_idx, track_id, label) stream into deduplicated violation episodes. Redesigned from the original "same track ID + N consecutive identical frames" plan after Day 12's findings - switched to majority-vote within a track's full lifetime (MIN_TRACK_FRAMES=5 to filter noise, MAJORITY_THRESHOLD=0.5 with ties resolved in favor of flagging) since strict consecutive-matching would miss violations on exactly the small/distant/occluded workers Day 12 showed suffer from label flicker. Explicitly reasoned through and documented that MIN_TRACK_FRAMES is an untuned intuition-based heuristic, and that the tie-breaking threshold is a deliberate recall-over-precision choice consistent with docs/eval.md. 7 unit tests passing, covering short-track filtering, exact-tie flagging, clear majority, majority-compliant suppression, no-violation tracks, competing violation types, and multi-track independence.

## Day 14 — CV integration (Checkpoint B)
Built src/inference_service.py: runs the fine-tuned model with ByteTrack on the test video, feeds raw (frame_idx, track_id, label) detections into Day 13's detect_episodes(), saves one evidence frame per episode, and POSTs each as a Violation event to the FastAPI service. Discovered the violations.violation_type column has no CHECK constraint (just TEXT NOT NULL) - decided to use the AI's real class names (e.g. "NO-Safety Vest") as the canonical convention going forward rather than matching Day 4's legacy seed.py naming ("no_vest"), accepting that old fake rows now use an inconsistent older convention. Full pipeline run end to end: 1704 raw detections -> 11 violation episodes -> 11 successful POSTs -> verified all 11 landed in Postgres with matching evidence files on disk. This is Checkpoint B: video -> detection -> tracking -> deduplication -> database, working and verified, not just claimed. Known simplification documented: timestamps are synthesized from script run time + frame offset since this is offline batch processing, not a live stream (arrives Week 3).

## Day 15 — Kafka Setup & the Consumer Offset Bug

Added Apache Kafka (KRaft mode, single-node, no Zookeeper) to docker-compose.yml,
alongside the existing Postgres/Adminer services. Created two topics, `frames`
and `events`, matching the two data flows the streaming pipeline will need:
raw frame metadata and detected violation events.

Hit a real bug testing basic produce/consume with the CLI tools: messages sent
via kafka-console-producer.sh never appeared in kafka-console-consumer.sh, even
with --from-beginning, even sent non-interactively via a piped echo command.
Topic health checks (kafka-topics.sh --describe) came back completely clean,
which ruled out a broken topic and pointed toward something server-side.

Root cause, found in `docker compose logs kafka`: Kafka couldn't create its
internal `__consumer_offsets` topic (where every consumer group's read progress
is tracked) because that topic defaults to a replication factor of 3, and this
single-node dev cluster only has 1 broker. Kafka retried and failed to create
it every second, forever, which meant consumers could never register progress
and just sat silently deaf — looking exactly like "messages aren't arriving,"
even though the producer side worked the entire time.

Fix: set KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 in docker-compose.yml, since
a single broker can only ever hold 1 copy anyway. After that, produce/consume
worked immediately.

Followed up with a Python producer/consumer pair (kafka-python) sending real
JSON messages instead of plain strings, then explicitly tested consumer group
offset persistence: ran the consumer, killed it, produced a new batch while it
was down, restarted it, and confirmed it picked up only the new messages (not
a replay of the old ones) — proving Kafka remembers a consumer group's progress
across restarts, which is the actual property that will matter once a real
ingestion service is reading from this pipeline and needs to survive crashes
without losing or duplicating data.

## Day 16 — Decoupling the CV Pipeline from the API via Kafka

Wired Kafka into the real pipeline instead of just testing it in isolation.
inference_service.py no longer calls requests.post() directly against the
API — it now publishes each violation event as JSON onto the Kafka `events`
topic and moves on immediately. A new script, event_consumer.py, subscribes
to `events` and does the actual POST to the API, using the consumer group
pattern proven out on Day 15.

The reason: a direct HTTP call ties the CV pipeline's success to the API
being up and responsive at that exact moment. Putting Kafka in between means
the pipeline never blocks on or depends on anything downstream — it just
publishes and trusts Kafka to hold the data safely.

Proved this wasn't just theoretical: killed the consumer, reran the full
detection+tracking+episode pipeline (11 violations, same as Day 14's run),
and confirmed via curl that the database did not grow at all — the 11 new
events were sitting safely in Kafka with nothing to read them. Restarted
the consumer and watched it immediately process all 11 backlogged events
(POST status 200 each), confirmed by the violation count in the database
jumping by exactly 11. Zero data loss, zero duplicates, no manual
intervention needed to recover.

This is the actual point of this whole Kafka detour: the pipeline is now
resilient to the API or its consumer going down temporarily, which matters
once this is running unattended against a real camera stream instead of a
single test video.

## Day 17-18 — From Batch File to Live RTSP Stream

Replaced the static test video file with a real streaming source. Added
MediaMTX (a lightweight RTSP server) to docker-compose.yml, and used ffmpeg
to loop the existing test video and push it into MediaMTX as a simulated
live camera feed (`-re -stream_loop -1 ... -rtsp_transport tcp`). The
`-rtsp_transport tcp` flag was required after an initial attempt failed:
RTSP's default UDP transport uses dynamically-negotiated ports that Docker's
port mapping never exposed, so the stream died with a broken pipe a few
seconds in. Forcing RTSP to tunnel everything through the single mapped TCP
port fixed it immediately.

Confirmed the stream was genuinely readable at two levels before touching
the real pipeline: raw OpenCV (`cv2.VideoCapture`) and then `model.track()`
itself, both pointed directly at the RTSP URL instead of a file path.

The real engineering problem this phase was about: `episodes.py`'s original
design assumed a finished, complete list of detections (fine for a batch
file, since you only call it after reading the whole video). A live stream
never finishes, so there's no "video ended" moment to wait for. Solved this
by refactoring the per-track majority-vote decision into its own reusable
function (`evaluate_track`), then built `live_inference_service.py`, which
tracks every open track's buffered frames and "closes" a track (runs the
same violation decision, publishes to Kafka if it qualifies) once that
track hasn't been seen for TRACK_TIMEOUT frames - i.e., it's inferred the
person left the scene or tracking lost them. Confirmed via the existing
7-test suite that this refactor didn't change the batch pipeline's behavior
at all.

Ran the full live chain for ~40 seconds: ffmpeg -> MediaMTX -> live YOLO
tracking -> online episode closing -> Kafka `events` -> event_consumer.py
-> API -> Postgres. Every closed track with a violation was published and
POSTed successfully (confirmed via the consumer's 200 statuses and the
violation count in the database growing from 5038 to 5436). Also noted and
understood why track IDs climbed so fast: the looped video creates an
abrupt discontinuity every ~4.84 seconds that ByteTrack has no way to
recognize as "the same video restarting," so it assigns entirely new IDs
every loop - a real tracker limitation, not a bug in this code.

Known simplification carried forward: evidence frame extraction isn't
implemented yet for the live path (evidence_uri is null), since the
batch script's seek-to-frame approach doesn't apply to a live stream that
isn't being buffered.

## Day 19 — Data Lake: Bronze and Silver Tiers via LocalStack

Added a data lake layer so raw pipeline output stops disappearing once
processed. Concept: bronze is raw, untouched data (here: per-frame
detections exactly as the model produced them, before any cleaning);
silver is cleaned, decision-ready data (here: the deduplicated violation
episodes from episodes.py, same data that goes to Kafka/Postgres, archived
independently). Gold (aggregated, dashboard-ready summaries) is deferred to
Week 4 alongside the Streamlit dashboard, since gold is shaped around
whatever's consuming it, and that consumer doesn't exist yet.

The actual motivation: right now, once detect_episodes() runs, the raw
per-frame detections are gone forever. If a bug is ever found in the
episode-detection logic (like Day 12's label-flicker discovery), there
would be nothing to reprocess from. Bronze storage fixes that.

Hit two real infrastructure surprises getting the storage layer itself
running, both from changes that happened industry-wide just days before
this session:
1. MinIO removed its images from both Docker Hub (Sept 11) and Quay
   (Sept 24) entirely - no amount of correct docker-compose config would
   have worked, since the images themselves no longer exist publicly.
2. Pivoted to LocalStack (an AWS emulator, using the real boto3 SDK -
   arguably more transferable than MinIO's own client would have been),
   but :latest now requires a LocalStack account and auth token after
   their community/pro tier merge in March 2026. Fixed by pinning to
   4.4.0, the last version before that merge.

Both were genuine "the ground shifted under a standard tutorial" problems,
diagnosed via actual error logs and targeted searches rather than guessing -
same debugging discipline as the Kafka and RTSP issues earlier this week.

Verified end to end: ran inference_service.py, confirmed via a separate
boto3 listing script that bronze/<run_id>/detections.json (29.9KB, all 1704
raw detections) and silver/<run_id>/episodes.json (1.4KB, all 11 cleaned
episodes) both landed in the safesite-datalake bucket, while the existing
Kafka -> consumer -> API -> Postgres path kept working unchanged alongside it.

**Addendum**: Ayman caught that the data lake archiving only existed in the
batch inference_service.py, not the live streaming pipeline from Days 17-18
- a real gap, since the point of the reliability review in Days 20-21 is to
test the actual production path (live streaming), not the offline one.
Fixed by archiving per-track instead of per-run in live_inference_service.py
(since a live stream has no single "finished" moment to archive everything
at once): bronze gets every closed track regardless of outcome, silver gets
only the ones that qualified as violations. Verified via a live run: bronze
held one file per closed track (~280 files), silver held exactly 29 files,
matching the 29 "Closed track -> Published" lines printed during the run -
confirming the filtering logic works correctly, not just assumed.

## Days 20-21 — Checkpoint C: Reliability Review

Closed out Week 3 with a deliberate reliability review of the live
streaming pipeline (not the offline batch one) - three targeted failure
tests, each with a prediction made before testing, verified against real
output rather than assumed from good architecture alone. Full writeup in
docs/reliability_review.md.

Found and fixed a genuine silent-data-loss bug: event_consumer.py relied
on Kafka's default auto-commit, which advances past a message the instant
it's handed to the consumer loop - regardless of whether the code actually
succeeded at anything with it. Killing Postgres mid-stream proved this:
the API returned 500, the consumer logged it and moved on, and the
violation was permanently gone once Postgres came back - Kafka had already
considered it delivered. Fixed with manual offset commits, retry-with-
backoff, and a dead-letter file for anything that still fails, plus a
replay script. Re-verified the full loss-and-recovery loop live.

Tested Kafka itself going down from both sides of the pipeline: a fresh
consumer fails loudly and immediately (good - unambiguous, restart-able).
The live producer, already running, failed completely silently - send() is
async and the code never checked the result - but, surprisingly, fully
recovered every backlogged event once Kafka came back, because kafka-
python buffers unsent messages in memory and retries automatically. The
real finding wasn't data loss here, it was the complete lack of visibility:
that backlog could grow for a long time with zero signal, and only
survives as long as the producing process itself doesn't crash or restart
during the outage - a real blind spot for production.

Measured actual live throughput instead of assuming the pipeline was fast
enough: 6.33 fps against a 29.97 fps source, only 21.1% of real-time.
Isolated the cause by measuring decode-only (no model) separately: 58.0%,
revealing two stacked bottlenecks instead of one. Investigating led to
finding a real, independent bug: model.device reported "cpu" despite
torch.cuda.is_available() being True - Ultralytics' model.track() was
never explicitly told to use the GPU, so it had been running on CPU this
entire project, including Checkpoints A and B, without ever affecting
detection quality (only speed), which is exactly why it went unnoticed.
Fixed by adding device=0 to every model.track() call; re-measured at 34.9%
of real-time, confirmed via re-running the batch pipeline that results
were unchanged (1704 detections, 11 episodes either way). Documented the
remaining gap (now decode-bound, not inference-bound) as a known
limitation requiring GPU-accelerated video decode to fully close - real
infrastructure work, correctly out of scope to improvise today.

Reaching Checkpoint C this way - actually breaking things on purpose and
measuring real numbers, rather than assuming the architecture was
resilient and fast because it was designed with Kafka and a GPU in mind -
is exactly the discipline this whole project has tried to practice since
Day 1, and it caught two genuinely significant, previously invisible bugs.
