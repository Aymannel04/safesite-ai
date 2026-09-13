# SafeSite AI — Solo Roadmap & Learning Path

**This document supersedes `ROADMAP.md` and `ROADMAP_V2.md`.** You're now running this project solo. That changes two things for the better: the full RTX 4060 is yours for every workload (no splitting with a weaker GPU), and there's no coordination overhead — but it also means no one else covers ground while you sleep, so scope discipline matters more, not less.

**Method, unchanged and non-negotiable:** for every technology, **learn first (what/why/how, in real depth) → apply it immediately in the project**. Never build with a tool before its Learn block. Never accept AI-generated code (Claude Code or otherwise) you can't explain line by line — after it writes something, ask it "explain this line by line" and "why this way and not X", then be able to redraw the logic from memory.

**Duration:** 6 core weeks (~30 focused days, 3–5 h/day) + optional stretch week. Solo means the calendar can flex — the sequencing shouldn't.

---

## How each day works

1. **Learn (45–60 min):** read the concept below, plus one external resource. Write 5 sentences in your own words in `docs/LESSON_XX.md` — if you can't, you haven't learned it yet.
2. **Isolated exercise (60–90 min):** a tiny, throwaway script proving you understand the concept, disconnected from the real project.
3. **Integrate (90 min):** apply it directly inside SafeSite AI. This is the only code that ends up in the repo.
4. **Inspect & explain aloud (20 min):** look at the logs/data it produced, explain the flow out loud as if to an interviewer.
5. **Commit + journal (10 min):** one coherent commit, one line in `JOURNAL.md` ("what I built, what broke, what I learned").

Skipping steps 1 and 4 is how people end up with a finished project and an empty head at the whiteboard. Don't.

## Core principles

- **Vertical slice first.** From Day 3 onward, a complete (if ugly) system exists end to end. Every week upgrades a working thing rather than assembling disconnected parts that meet at the end.
- **Contract-first.** The violation event schema is frozen early (Day 6) and every later stage — fake data, real YOLO, Kafka, the agent — speaks the same contract. That's what lets you swap a fake producer for a real one without breaking anything downstream.
- **GPU is yours — use it, but sequentially.** The RTX 4060 (8 GB VRAM) comfortably runs YOLOv8s fine-tuning, and separately runs a quantized 8B LLM via Ollama. It will NOT comfortably run YOLO + the LLM + a vision-language model all loaded at once. Plan for one heavy GPU citizen at a time; Ollama unloads models automatically when idle.
- **Checkpoints are safety nets, not suggestions.** Each one below is a recorded, working demo. If later weeks slip, you already have something to show.
- **Cut from the bottom of the priority list, never the top,** if you run short on time (see the end of this document).

---

# Week 0 — Setup (Days 1–2)

### Day 1 — Environment & terminal

**Learn — what/why:** A "shell" is a text interface to your OS; almost all real infrastructure (Docker, Git, Python tooling) is driven from one, because GUIs don't scale to reproducible, scriptable work. On Windows, **WSL2** gives you a real Linux environment, which is what Docker and most data-engineering tools assume.
- What: `cd`, `ls`, `pwd`, `mkdir`, `cp`, `mv`, `rm`, `cat`, `less`.
- Why it matters: pipes (`|`) and redirection (`>`, `>>`) let you chain small tools into pipelines — the same philosophy behind Kafka later.
- Resource: MIT's *Missing Semester*, lecture 1.

**Apply:** Install WSL2 (Ubuntu) + Docker Desktop + Git. Create a folder tree for the project by hand in the terminal (no GUI). Chain 3 commands with a pipe (e.g. `cat file | grep word | wc -l`).

**Done when:** you can navigate, create, search, and chain commands without touching a file explorer.

### Day 2 — Git properly + Python as a project

**Learn — what/why:** Git is a time machine for code: every commit is a snapshot you can return to; branches let you try things without breaking `main`. Working solo, you might be tempted to skip branches — don't, because (a) it's what you'll be evaluated on doing correctly in any job/PhD lab, and (b) a bad experiment on `main` with no branch history is un-undoable.
- What: `init/add/commit/status/log/diff`, the three zones (working → staging → history), branches (`checkout -b`), `.gitignore`.
- Python-as-project: virtual environments (why isolation matters — two projects needing different library versions), `requirements.txt`, module structure (`src/`, `import`, `if __name__ == "__main__"`), `logging` instead of `print`.
- Resource: [learngitbranching.js.org](https://learngitbranching.js.org/) (Main section); Python docs tutorial ch. 6 & 8.

**Apply:** Create the GitHub repo: `src/`, `docs/`, `database/`, `docker/`, `learning/`, `failure_cases/`, `JOURNAL.md`, `LATER.md`, `README.md`. Copy in `FICHE_DE_CADRAGE.md`, `architecture.png`, this roadmap into `docs/`. Make a branch, add a "hello" Python module runnable as `python -m src.main`, merge it via a self-reviewed PR (read your own diff critically — that's the habit).

**Done when:** repo exists with proper structure, `venv` + `requirements.txt` work, hello module runs, first PR merged.

---

# Week 1 — Vertical slice: fake events → API → database (Days 3–7)

**Outcome:** fake violations flow through a real API into a real database. This is the skeleton every later week builds on.

### Day 3 — Docker, deeply

**Learn — what/why:** A container packages an app with everything it needs so it runs identically anywhere — solving "works on my machine." An image is the recipe; a container is the running cake. Docker Compose describes a multi-container stack (our future ~7 services) in one YAML file.
- What: image vs container, `Dockerfile`, **volumes** (data surviving a restart — without one, your database resets every time you restart it), **networks** (containers reach each other by service name, not `localhost`), port mapping.
- Resource: [docker-curriculum.com](https://docker-curriculum.com/), then Compose quickstart.

**Apply:** `docker-compose.yml` with PostgreSQL + Adminer (a DB web UI). Confirm data survives `docker compose down && up`. Explain to yourself why.

**Done when:** you can browse the (empty) DB via Adminer; you can kill and restart the stack without losing data.

### Day 4 — PostgreSQL & SQL on real data

**Learn — what/why:** Relational databases store structured data with guarantees (types, constraints, keys) that a CSV can't. SQL is how you ask questions of that data.
- What: tables, primary/foreign keys, `SELECT/WHERE/ORDER BY`, `GROUP BY` + aggregates, `JOIN` (draw the Venn diagram), a basic index and why it speeds up lookups.
- Resource: [SQLBolt](https://sqlbolt.com/) end to end (2–3 h, worth it).

**Apply:** Design and create `database/init/001_schema.sql`: `cameras` and `violations` tables (id, camera_id, track_id, violation_type, confidence, started_at, ended_at, evidence_uri). Write `seed.py` inserting 5,000 realistic fake events. Write the 5 queries your future dashboard needs (per hour, per camera, compliance rate, top violation types, latest 20) into `docs/queries.sql`. Add an index on `started_at`, compare `EXPLAIN ANALYZE` before/after.

**Done when:** all 5 queries return sensible numbers; you can explain why the index helped (or didn't).

### Day 5 — HTTP, JSON, and FastAPI

**Learn — what/why:** Services talk to each other over HTTP by exchanging JSON. A REST API exposes URLs that return data instead of web pages. FastAPI validates input automatically (via Pydantic) and documents itself.
- What: request/response, methods (GET/POST), status codes (200/404/422/500), what a Pydantic model buys you (rejecting bad input before your code even runs).
- Resource: official FastAPI tutorial, "First Steps" + "Path Parameters" + "Request Body".

**Apply:** `src/api/`: `POST /violations` (validated insert), `GET /violations` (filters: camera, type, time range, limit), `GET /stats/daily`. Containerize it into the compose stack. Explore `/docs` (Swagger) — a stranger should be able to use your API from that page alone.

**Done when:** you can insert and query real rows through the API, not just via SQL directly.

### Day 6 — Contracts & tests

**Learn — what/why:** A "contract" is the agreed shape of data between components — freezing it early is what lets you replace a fake data source with a real one later without breaking anything downstream. Tests document intended behavior and catch regressions before they cost you a debugging afternoon.
- What: unit test vs integration test, why a broken constraint should fail loudly, semantic versioning of a schema (v1, v2...).

**Apply:** `pytest` tests: valid insert, invalid confidence (>1 or <0) rejected, filters work. Break a DB constraint on purpose (insert a null into a NOT NULL column) and read the failure. Write `docs/contracts.md` freezing **violation event v1** (exact field names/types) — this is the single most important artifact of the week; everything from Week 2 onward must match it exactly.

**Done when:** tests pass, contract v1 is written down, and you understand *why* freezing it matters.

### Day 7 — Review & video fundamentals

**Learn — what/why:** Video is just a sequence of images (frames) at a rate (FPS); processing every frame of a 30fps stream for a slow-changing thing like PPE compliance is wasteful — sampling trades a little latency for a lot of compute saved.
- What: frame, FPS, resolution, codec (just the concept — you don't need codec internals), why sampling is a deliberate engineering choice, not a shortcut.
- Resource: any 20-min "video processing basics" primer + OpenCV's official "Getting Started with Videos" tutorial.

**Apply:** Read a downloaded construction-site video (Pexels/Pixabay) frame by frame with OpenCV, save 1 frame/second to disk. Measure processing time at full resolution vs half resolution.

**Also today:** redraw the current architecture from a blank page (video → future ingestion → future CV → API → DB), no notes. Fix documentation gaps, not new features.

> ✅ **CHECKPOINT A:** `docker compose up` gives you a seeded, queryable database behind a tested, documented API. Record 60 seconds of it working. You now have proof of a real system, however simple.

---

# Week 2 — The brain: computer vision core (Days 8–14)

**Outcome:** a real video produces deduplicated PPE violation events flowing through the same API from Week 1.

### Day 8 — Detection theory (the one full theory day — don't rush it)

**Learn — what/why, in real depth (this is PhD/interview material):**
- Classification ("this image has a helmet") vs. **detection** ("there's a person HERE with confidence 0.9, and they have no helmet") — boxes + classes + confidence, not just a label.
- **IoU** (Intersection over Union): how you measure whether a predicted box matches a real one.
- **NMS** (Non-Max Suppression): why a detector proposes many overlapping boxes for one object, and how duplicates get filtered.
- **Precision** (of what I flagged, how much was correct) vs **recall** (of what was really there, how much did I catch) — and why, for safety, **missing a real violation (low recall) is worse than a false alarm (low precision)**. This asymmetry should drive your threshold choices later.
- **mAP** (mean Average Precision): the standard detection metric, what it averages over, and what it can hide (e.g., a model can have decent mAP while failing badly on the one class you care most about).
- **Transfer learning / fine-tuning:** why you start from a model pretrained on millions of generic images (COCO) and adapt it with a few thousand PPE images, instead of training from zero — the pretrained model already knows "edges, shapes, what an object boundary looks like"; you're only teaching it the new classes.
- Resource: Ultralytics docs "How YOLO works"; any solid "mAP explained" article; work through precision/recall **by hand** on 10 made-up detections (TP/FP/FN) until it's automatic.

**Apply:** Write `docs/eval.md`: your metrics, your train/val/test split plan, your mAP target (0.75 @50), and a paragraph justifying why you'll tune thresholds toward recall.

**Done when:** you can compute precision/recall from a confusion table by hand, no notes, and explain mAP to a rubber duck.

### Day 9 — Pretrained YOLO, hands-on

**Learn — what/why:** Ultralytics YOLO's API abstracts training/inference behind a few functions; understanding the data format (one `.txt` label file per image: `class x_center y_center width height`, normalized 0–1) demystifies what "training" actually consumes.

**Apply:** Install Ultralytics; confirm GPU is used (`device=0`); run pretrained `yolov8s` on a construction-site video — boxes should appear (generic classes only, no PPE yet). Open a few label files from a downloaded dataset by hand and match them to the image.

**Done when:** you've watched raw pretrained detection run on your own GPU and understand the label format well enough to write one by hand.

### Days 10–11 — Fine-tune on PPE

**Learn — what/why:** Fine-tuning hyperparameters that matter at your scale: image size (larger = more accurate, slower, more VRAM), batch size (limited by VRAM), epochs (too few = underfit, too many = overfit — watch the validation curve, not just training loss), and basic augmentation (flips, brightness jitter) that helps generalization to varied lighting — directly relevant to your later drift story.

**Apply:** Download the Roboflow Construction Site Safety dataset (has NO-Hardhat/NO-Vest negative classes — exactly what you need for violations). Fine-tune `yolov8s` on the 4060 with a real image size (640). Evaluate: per-class mAP, confusion matrix, precision/recall curves. Manually inspect 20 failure cases (small people, occlusion, odd angles) and save them with notes into `failure_cases/` — this becomes real evidence for your report's limitations section, which academic juries specifically reward.

**Done when:** mAP@50 ≥ 0.75 overall, or a written, evidence-based explanation of why not and what you'd try next.

### Day 12 — Tracking

**Learn — what/why:** A detector has no memory between frames — the same person missing a helmet in 100 consecutive frames looks like 100 unrelated events unless something links them. **Tracking-by-detection** (ByteTrack) assigns a persistent ID to each detected person across frames by matching boxes frame-to-frame (motion + appearance cues). **ID switches** — when tracking incorrectly swaps two people's IDs (e.g., after they cross paths) — are the main failure mode and a great interview topic.

**Apply:** Run `model.track()` (Ultralytics has ByteTrack built in) on a multi-person video; draw persistent IDs on screen; find and screenshot at least one ID switch. Define a **violation episode** in `docs/contracts.md` v2: same camera + track_id + violation_type, sustained for N consecutive frames (debouncing — this stops one flicker of a missed detection from creating a false event).

**Done when:** you can point to an ID switch in your own footage and explain what likely caused it (occlusion, crossing paths, fast motion).

### Days 13–14 — CV integration

**Learn — what/why:** This is where detection + tracking + business logic (the debounce rule) become a service that speaks your Week-1 contract — the moment "a machine learning model" becomes "a component of a system."

**Apply:** Build `src/inference/`: reads the video (or webcam), runs YOLO+ByteTrack, applies the debounce rule per track, and on a confirmed violation, saves an evidence frame locally and `POST`s a contract-v1 event to your Week-1 API. Run it end to end on a full test video.

**Done when:** one worker without a helmet in a test video produces exactly ONE violation row in the database, with a real evidence image you can open.

> ✅ **CHECKPOINT B — the safety net:** video → YOLO+ByteTrack → deduplicated violation → API → database, with visual evidence. **Record this.** From this point forward, you already have a demoable project no matter what happens later — everything after is enrichment, not survival.

---

# Week 3 — Streaming & the data lake (Days 15–21)

**Outcome:** ingestion and inference become independent services connected by a message broker; evidence is organized as a proper data lake instead of local files.

### Days 15–16 — Kafka

**Learn — what/why, in depth:** Right now your inference script reads video directly — fine for one file, but real systems need ingestion (reading cameras) decoupled from inference (running the model), because they run at different, unpredictable speeds. A **message broker** is a durable queue: producers publish messages to named **topics**; consumers read them independently, at their own pace, and can be killed/restarted without losing data (tracked via **offsets**, a bookmark of what's been read). **Consumer groups** let multiple consumers share the load of one topic.
- Concretely: what happens to a topic's backlog (**queue lag**) when the inference consumer is slower than the ingestion producer? (It grows — and now you can *measure* system health instead of guessing.)
- Resource: Confluent's free "Kafka 101" video course, concepts 1–8.

**Apply:** Kafka in `docker-compose.yml`; two topics: `frames` (metadata + frame reference, NOT raw pixels — measure why before you'd ever put pixel bytes on a queue) and `events`. Write a minimal producer and consumer in Python, send/receive real JSON messages. Kill the consumer for 2 minutes, restart it, watch it resume from its last offset — this is the core guarantee Kafka gives you.

**Done when:** you can explain, with your own demo, why a broker beats direct service-to-service calls — and you've watched offset-based recovery happen.

**Fallback:** if Kafka configuration eats more than 2 days, switch to Redis Streams (same producer/consumer pattern, far less operational overhead) and document the trade-off in `JOURNAL.md` — this decision, explained, is worth more in an interview than a working Kafka you can't defend.

### Days 17–18 — Real ingestion service

**Learn — what/why:** Separating "read the camera" from "run the model" is the actual data-engineering skill here — it's what lets you later add a second camera, or swap the model, without touching the other half.

**Apply:** MediaMTX serves your test videos as real RTSP streams (so the rest of the system genuinely doesn't know it isn't a physical camera). `src/ingestion/` reads the RTSP stream via OpenCV, samples at 5fps, stamps camera_id + timestamp, publishes to `frames`. Your Day 13–14 inference service becomes a pure Kafka consumer of `frames`, publishing violation events to `events` (a separate small consumer writes `events` into Postgres via the API). Add structured logging and basic reconnection handling if the stream drops.

**Done when:** ingestion and inference run as two separate processes/containers, connected only through Kafka, and you can restart either independently without crashing the other.

### Day 19 — MinIO & the medallion architecture

**Learn — what/why:** A database is bad at storing large binary blobs (videos, images) — you want cheap, schema-free **object storage** for that. MinIO is a self-hosted, API-compatible clone of Amazon S3, so everything transfers directly to real cloud skills. The **medallion pattern** — bronze (raw, immutable) / silver (cleaned/annotated) / gold (aggregated) — exists because raw data should never be overwritten: if your processing logic has a bug, you can always recompute silver/gold from bronze; you can never undo throwing away the raw data.

**Apply:** MinIO in compose. Ingestion archives raw clips/frames to `bronze/`. The inference service saves annotated evidence frames + detection JSON to `silver/` instead of local disk. `src/lake.py` (using `boto3`) is the shared helper both services import. `evidence_uri` in your events now points at a real MinIO object.

**Done when:** you can browse bronze and silver in MinIO's web UI and every `evidence_uri` in your database resolves to a real image.

### Days 20–21 — Reliability review

**Learn — what/why:** Production systems are judged on how they fail, not just how they succeed. This is the week to deliberately break things and measure, rather than hope.

**Apply:** Test and document each: a slow consumer (artificially sleep in the inference loop — watch queue lag grow), a broker restart mid-stream, an invalid event (malformed JSON — does it crash the consumer or get safely rejected?), a duplicate event (replay the same message — does your debounce logic double-count?). Measure and record in `JOURNAL.md`: throughput (events/sec), average queue lag, inference latency per frame, dropped-frame rate. Update `docs/ARCHITECTURE.md` to match what you actually built (not what you planned).

> ✅ **CHECKPOINT C:** kill any single service mid-run — nothing is silently lost, and the system recovers on restart. You can now answer "what happens when inference is slower than ingestion?" with a real measurement, not a guess.

---

# Week 4 — Product & MLOps (Days 22–27)

**Outcome:** a monitored, explainable, self-aware system — the layer that separates a class project from a production-style platform.

### Days 22–23 — Streamlit dashboard

**Learn — what/why:** Streamlit turns a Python script into a web dashboard without writing HTML/CSS/JS — appropriate here because the point is showing your data pipeline's output, not building a frontend. It should call your API, never the database directly — respecting the same layering you built in Week 1.

**Apply:** KPI cards (violations today, compliance %, cameras online), a violations-per-hour chart, an evidence gallery pulling images from MinIO/silver, filters by camera/type/date, auto-refresh every 10s.

**Done when:** a new violation appearing in the pipeline shows up on the dashboard within seconds, live, without a manual refresh.

### Day 24 — MLflow

**Learn — what/why:** Right now, "which exact model weights are running, and how were they trained?" has no good answer — you'd have to remember. **Experiment tracking** (MLflow) logs every training run's parameters/metrics/artifacts automatically; the **model registry** gives trained models version numbers and stages (staging/production), so your inference code loads "the current production model" by name instead of a hardcoded file path — this is what makes rollback possible.

**Apply:** Retroactively wrap your Week-2 YOLO fine-tuning in MLflow logging (or rerun it). Compare at least 2 runs in the MLflow UI (e.g., different image sizes or epoch counts). Register your best model as `ppe-detector` v1. Refactor the inference service to load the model from the registry, not a local path. Perform one deliberate rollback to a previous version to prove the mechanism works.

**Done when:** you can answer, live, "what's currently in production and how was it trained?" — and demonstrate a rollback.

### Day 25 — Data quality & drift

**Learn — what/why, this is a differentiator:** A model can be perfectly accurate on paper and still fail silently in production because the *world* changed — new lighting, rain, a repositioned camera. This is **data drift** (inputs changed) as distinct from **concept drift** (the input→output relationship itself changed). You can't monitor production accuracy directly because you don't have labels for live footage — so you monitor *proxies*: input statistics (brightness, blur, detection confidence distributions) and compare a recent window against a trusted reference window. Also: basic **data quality validation** (nulls, allowed enum values, confidence ∈ [0,1], timestamp sanity) — the unglamorous checks that stop garbage data from silently corrupting your dashboard.

**Apply:** Hand-written validation checks on incoming events (or Great Expectations if time allows) wired into the events consumer. Using Evidently (or a simple statistical comparison you write yourself), compute brightness/blur/confidence distributions on your normal test video vs. an FFmpeg-darkened "night" version of the same video, and generate a drift report. **Build this into a repeatable demo scenario**: stream the darkened video and watch a drift alert fire on its own, with no manual intervention. This single scenario ("the system notices its own environment changed") is one of the best 30 seconds of your demo.

**Done when:** the night-footage scenario reliably triggers a visible alert, and you can articulate why accuracy alone can't be monitored in production.

### Days 26–27 — The local LLM agent (core, not optional — this is on your GPU now)

**Learn — what/why, in depth:** An LLM that only replies to text is a chatbot; an **agent** can *act* — it decides to call tools you expose (e.g., "run this SQL query"), reads the result, and continues reasoning, in a loop, until it can answer. **Ollama** runs open models (Llama 3.1 8B) locally with an OpenAI-compatible API; **quantization** (storing weights in 4 bits instead of 16) is what lets an 8-billion-parameter model fit in 8GB VRAM, trading a small amount of quality for a huge memory reduction. **LangGraph** represents the agent's reasoning loop as an explicit graph of nodes (LLM call, tool execution) and edges, which makes it debuggable — you always know which step failed. The two things that make an agent trustworthy instead of a liability: giving it a **read-only** database credential (it can never modify data even if it tried), and validating that any SQL it generates is a `SELECT` before executing it — plus instructing it to answer *only* from query results, never from its own "knowledge" of typical numbers (this is how you prevent hallucinated statistics).

**Apply:** Add Ollama to compose with GPU passthrough; pull `llama3.1:8b`. Build a LangGraph agent with two tools: `get_schema` (returns your table structure) and `run_sql` (executes validated, read-only SELECT queries against Postgres). Build a 20-question evaluation set in `docs/agent_eval.md` (e.g., "how many helmet violations yesterday?", "which camera has the most violations?", plus a couple of out-of-scope questions it should correctly refuse) with expected answers, and measure your pass rate (target ≥16/20). Always display the generated SQL alongside the answer — this transparency is itself a selling point in interviews.

**Done when:** the agent answers real questions correctly against your real events database, refuses out-of-scope questions, and every answer is traceable to a visible, validated SQL query.

---

# Week 5 — Hardening & delivery (Days 28–30+)

### Day 28 — Hardening

**Apply:** Boot the entire stack from a clean state (`docker compose down -v && up`) and confirm it works with zero manual steps beyond that command. Run a 30-minute continuous demo, monitoring CPU/RAM/GPU/VRAM usage and noting any failures. Fix only what threatens the demo — resist the urge to add features now.

### Days 29–30 — Delivery package

**Apply:**
- **Demo video (3–5 min):** live stream → violation detected → evidence appears → dashboard updates → agent answers "how many violations today?" with visible SQL → darkened-video drift alert fires. Script it before recording.
- **README:** problem statement, final architecture diagram, quickstart (`docker compose up` and nothing else), a results table (mAP per class, agent eval score, throughput/latency numbers from Week 3), and an honest limitations section built from your `failure_cases/` folder.
- **Report**, built from `JOURNAL.md` and your decision log (e.g., Kafka-vs-Redis-Streams if that came up, threshold choices, VRAM sequencing strategy).

### Interview & defense prep (ongoing from Day 28, not a last-minute cram)

- The 90-second pitch, rehearsed out loud until it's smooth.
- A 5-minute whiteboard walkthrough of the full architecture, from memory, no notes.
- Written answers to the 12 questions below.
- One well-told "hardest problem I solved" story (VRAM sequencing, an ID-switch bug, making the agent trustworthy — pick your realest one).

> ✅ **FINAL CHECKPOINT:** a stranger can run the whole system with one command; you can defend every arrow on the architecture diagram unprompted; the demo video exists and works.

---

# Stretch goals (only after Day 30)

In priority order: 1) a second simultaneous camera stream, 2) Airflow for nightly aggregation into Parquet "gold" tables, 3) replacing hand-rolled data-quality checks with Great Expectations, 4) a vision-language model (Qwen2-VL) for natural-language frame descriptions, layered onto the agent.

## Scope priorities — cut from the bottom if time runs out

**Must:** one video stream · helmet+vest detection · tracking + deduplication · Postgres + FastAPI + dashboard · reproducible Docker setup · measured evaluation (mAP, failure cases).
**Should:** Kafka (or documented Redis Streams fallback) · MinIO bronze/silver · MLflow tracking + registry-based loading · drift detection + the night-footage demo scenario · the local LLM agent.
**Stretch:** second camera · Airflow + gold layer · Great Expectations · vision-language model.

## Interview questions — answer all of these without notes before you call it done

1. Why is the system event-driven instead of one large Python script?
2. Why does Kafka carry references/metadata instead of raw video — what is a broker, and what is it explicitly *not* (a database, a data lake)?
3. Why are violation events, evidence images, and aggregates stored in three different systems?
4. How does tracking prevent duplicate violation counts? What is an ID switch and what causes one?
5. What does mAP measure, and what can a good mAP score still hide? Why does recall matter more than precision here?
6. What happens when inference is slower than ingestion — and what did you actually measure?
7. How do database constraints and validation checks protect against silent data corruption? Give a concrete example.
8. How would this architecture need to change to support 100 real cameras?
9. How do you stop the LLM agent from modifying data or inventing numbers it wasn't given?
10. Why fine-tune a pretrained model instead of training from scratch?
11. What is data drift, how does your system detect it, and why can't you just monitor accuracy directly in production?
12. What actually failed during this project, and what evidence led you to the fix?

---

*Companions: `FICHE_DE_CADRAGE.md` (formal scope doc — update its team section since it's now solo), `LEARNING_GUIDE.md` (original module-by-module reference, still valid for deeper dives), `architecture.png` (keep it current as you build).*
