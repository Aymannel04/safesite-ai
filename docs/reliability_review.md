# Reliability Review — Checkpoint C (Days 20-21)

Three targeted failure-mode tests against the real streaming pipeline (not
the offline batch one), each with a prediction made before testing and a
verified outcome, rather than assuming resilience from design intent alone.

## Test 1: Database outage while the consumer is running

**Setup:** `event_consumer.py` and the API running normally, Postgres
stopped mid-operation, one test violation published to the `events` topic.

**Original behavior (bug found):** The API correctly returned a 500 (it
couldn't reach the database), but `event_consumer.py` used Kafka's default
auto-commit, which advances the offset the instant a message is handed to
the consumer loop - regardless of what the code does with it afterward.
The consumer printed `POST status 500` and moved on. Once Postgres was
restarted, the violation was confirmed permanently absent from the
database: Kafka had already marked it as consumed and would never
redeliver it. Silent, total data loss, despite the system "looking"
resilient (no crash, no visible alarm).

**Fix:** Disabled auto-commit. Failed POSTs now retry up to 3 times with a
short delay; if still failing, the event is written to a local dead-letter
file (`data/dead_letter/events.jsonl`) *before* the offset is committed, so
nothing is lost silently. A replay script (`scripts/replay_dead_letter.py`)
reprocesses the file once the downstream issue is resolved.

**Re-verified:** repeated the same outage. Consumer printed 3 failed
attempts, wrote the event to the dead-letter file, and committed. After
restarting Postgres, running the replay script successfully delivered the
event, confirmed present in the database afterward.

**Lesson:** Kafka's delivery guarantee ("the consumer received this
message") is a different guarantee from "the consumer successfully
processed this message." Conflating them is how systems silently lose data
while every individual log line looks fine.

## Test 2: Kafka outage, compared on both sides of the pipeline

**Setup A - a fresh consumer starting while Kafka is already down:**
immediate, loud crash - `kafka.errors.KafkaTimeoutError: Unable to
bootstrap from localhost:9092`. This is actually the *good* failure mode:
unambiguous, impossible to miss, and a process supervisor could simply
restart it once Kafka recovers.

**Setup B - the live streaming service (`live_inference_service.py`)
already running when Kafka goes down:** continued running with zero
visible error. `producer.send()` is asynchronous by default - it hands the
message to a background thread and returns immediately without waiting for
delivery confirmation, and the code never checked the result. Episodes kept
closing and "publishing" the entire time Kafka was down, with no
indication anything was wrong.

**What actually happened to that data:** once Kafka came back online, every
single backlogged event (confirmed via the consumer) was delivered
successfully. kafka-python's producer holds unsent messages in an internal
memory buffer and keeps retrying in the background, flushing the whole
backlog through once the broker is reachable again.

**The real, more nuanced lesson:** that in-memory buffer only survives as
long as the *producing process itself* stays alive. If `live_inference_service.py`
had crashed or restarted at any point during the outage - not Kafka, the
Python process itself - every buffered event would have been lost
permanently, with no trace anywhere. And critically, there is zero
visibility into this: no metric, no log line, no warning that a backlog is
silently growing in memory. In production this is a real blind spot - the
system can quietly accumulate risk with no observable signal until
something else (a restart, a crash, a deploy) triggers data loss at the
worst possible moment.

## Test 3: Live throughput measurement, and an unrelated bug it surfaced

**Setup:** measured actual frames processed by `model.track()` against the
RTSP stream over a fixed 30-second wall-clock window, compared to the
camera's real frame rate (29.97 fps).

**Initial result:** 6.33 fps - 21.1% of real-time, falling behind by ~24
frames/second. To isolate the cause, also measured raw OpenCV decode
throughput with no model inference at all: 17.38 fps (58.0% of real-time).
This meant two separate bottlenecks were stacked: decoding alone already
couldn't keep up, and inference was costing significantly more time on top
of that.

**Bug found while investigating:** checked `model.device` directly - it
reported `cpu`. Despite CUDA being fully available (`torch.cuda.is_available()`
returned `True`, GPU correctly identified as the RTX 4060), Ultralytics'
`model.track()` was never told to actually use it - it silently defaulted
to CPU inference the entire time, including throughout Checkpoints A and B.

**Fix:** added `device=0` explicitly to every `model.track()` call, in the
test script and in both `inference_service.py` and `live_inference_service.py`.

**Re-measured:** 10.46 fps - 34.9% of real-time, up from 21.1%. Verified
the batch pipeline still produces identical results (1704 detections, 11
episodes) after the change, confirming this was a pure performance fix
with no behavior change.

**Remaining gap:** 34.9% now sits close to the 58.0% decode-only ceiling,
meaning the system is now primarily bottlenecked by CPU-bound RTSP H.264
decoding rather than wasted CPU inference time. Closing that remaining gap
would require GPU-accelerated video decoding (e.g., NVDEC) through the
OpenCV/ffmpeg capture backend - a real infrastructure change, not a
quick fix, and is documented here as a known limitation rather than
something attempted in this session.

**Lesson:** "it works" and "it works in real time" are different claims,
and neither should be assumed without measuring. This also caught a
genuinely significant bug (CPU-only inference since Day 12) that had gone
unnoticed because detection *quality* was never affected - only speed -
and nothing in the existing test suite or manual checks was set up to
surface it.

## Summary for Checkpoint C

| Failure mode | Behavior found | Status |
|---|---|---|
| DB down (consumer side) | Silent permanent data loss | Fixed: retry + dead-letter + replay |
| Kafka down (consumer start) | Loud immediate crash | Acceptable (fail-fast) |
| Kafka down (producer side, already running) | Silent, but recovered fully via in-memory buffering | Documented risk: buffer is volatile, zero visibility |
| Live throughput | 21.1% of real-time | Fixed GPU bug -> 34.9%; remaining gap is a documented decode-bound limitation |

None of these were found by assuming the architecture was resilient or
performant because it was "designed with Kafka and a GPU in mind." Each
was found by deliberately breaking a specific dependency or measuring a
specific number, predicting the outcome first, and verifying the actual
behavior against real output - the same discipline used throughout this
project since Day 1.
