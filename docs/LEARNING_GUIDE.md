# SafeSite AI — Learning Guide (Phase 0)

**Everything to learn BEFORE writing project code.** Pitched at beginner level — no prior knowledge assumed beyond basic Python notebooks.

> **How to use this guide:** work top to bottom. Each module has: *What it is* (plain words), *Why we need it*, *Learn* (free resources), *Do* (hands-on exercise), and *Self-check* (questions you must be able to answer out loud — these are literally interview questions). Don't skip the self-checks: being able to *explain* is what impresses recruiters and admission juries, not having used a tool once.

> **Learning with Claude Code:** you'll build this project with an AI assistant. Rule to actually learn: never accept code you can't explain. After it writes something, ask it "explain line by line", ask "why this way and not X?", then rewrite a small version yourself from memory. Use AI as a tutor, not a vending machine — otherwise you'll have a finished project and empty hands at the whiteboard.

**Time budget: ~2 weeks** (before Week 1 of the project plan). Foundations: 4–5 days. Tool modules: 1 module ≈ half a day.

---

## Part A — Foundations (4–5 days, non-negotiable)

### A1. Python beyond notebooks (1.5 days)

**What.** You know Python in notebooks. Real projects are *scripts and packages*: multiple `.py` files importing each other, run from the terminal, with dependencies listed in a file.

**Learn.**
- Virtual environments: why projects need isolated dependencies (`python -m venv`, `pip install`, `requirements.txt`).
- Project structure: modules, `import`, `if __name__ == "__main__":`, functions/classes organized in files.
- The bits of Python that notebooks hide: command-line arguments (`argparse`), environment variables, logging (`logging` module instead of `print`), exceptions (`try/except`).
- Resource: the official [Python tutorial](https://docs.python.org/3/tutorial/) chapters 6 (modules) and 8 (errors); Corey Schafer's YouTube videos on venv, modules, and logging are excellent.

**Do.** Convert any old notebook of yours into a small project: `src/` folder, 2–3 modules, a `requirements.txt`, runs with `python -m src.main --input data.csv`, logs to a file. No notebook.

**Self-check.** Why do virtual environments exist? What does `if __name__ == "__main__"` do? Why is `logging` better than `print` in production?

### A2. Linux terminal (0.5 day)

**What.** All the project's infrastructure (Docker, servers) is driven from a terminal. You need fluency, not expertise.

**Learn.** Navigation (`cd`, `ls`, `pwd`), files (`cp`, `mv`, `rm`, `mkdir`, `cat`, `less`), pipes and redirection (`|`, `>`), searching (`grep`), processes (`ps`, `kill`), permissions basics (`chmod`), `ssh` concept. Resource: [MIT's Missing Semester](https://missing.csail.mit.edu/) lecture 1–2.

**Do.** On Windows, install **WSL2** (Ubuntu) — you'll need it anyway for Docker. Do everything above inside it: create a folder tree, grep inside files, chain 3 commands with pipes.

**Self-check.** What does `|` do? Difference between `>` and `>>`? How do you find which process uses port 8000?

### A3. Git & GitHub properly (1 day)

**What.** Version control: a time machine + collaboration system for code. The project lives on GitHub; teamwork happens through branches and pull requests (PRs).

**Learn.**
- Local: `init, add, commit, status, log, diff`. The three zones (working dir → staging → history).
- Remote: `clone, push, pull`, origin.
- Team workflow: branches (`checkout -b`), merging, **merge conflicts** (provoke one on purpose — resolving them calmly is the skill), pull requests, code review.
- Resource: [learngitbranching.js.org](https://learngitbranching.js.org/) (interactive, do "Main" + "Remote" sections).

**Do.** With a teammate: both branch from main, edit the same line of the same file, open PRs, merge one, resolve the conflict in the second. Write a good commit message every time (verb + what + why).

**Self-check.** What's the difference between `git add` and `git commit`? What is a merge conflict and how do you resolve one? Why review a teammate's PR instead of pushing to main directly?

### A4. SQL solidly (1 day)

**What.** The language for querying relational databases. Your whole analytics layer AND your LLM agent depend on it (the agent writes SQL — you must be able to judge its SQL).

**Learn.** `SELECT/WHERE/ORDER BY`, `GROUP BY` + aggregates (`COUNT, AVG`), `JOIN` (inner vs left — draw the circles), subqueries, then window functions at a basic level (`ROW_NUMBER`, running counts). Resources: [SQLBolt](https://sqlbolt.com/) start to finish, then [pgexercises.com](https://pgexercises.com/) for real practice.

**Do.** On paper first: design the project's `violations` table (columns, types, primary key). Then write from imagination the 5 queries the dashboard needs (violations per hour, per camera, compliance rate per day, top violation types, latest 20 events).

**Self-check.** Explain a LEFT JOIN to a child. Why does `GROUP BY` exist? What's an index and why does it speed up queries?

### A5. How the pieces of ANY data system talk: APIs & JSON (0.5 day)

**What.** Services in our platform communicate by sending **JSON** (structured text) over **HTTP APIs** (URLs that return data instead of pages). Understanding request → response is the glue for everything.

**Learn.** What HTTP is (methods GET/POST, status codes 200/404/500), what JSON looks like, what a REST API endpoint is. Resource: any 20-min "REST API explained" video + play with `requests` in Python.

**Do.** From Python, call a free public API (e.g., open-meteo weather API), parse the JSON, print one field. Then pretty-print any JSON with `json.dumps(indent=2)`.

**Self-check.** What happens, step by step, when your code calls `GET /violations?camera=3`? What does status 404 vs 500 mean?

---

## Part B — Infrastructure modules (each ≈ half a day)

### B1. Docker — run anything anywhere

**What.** A container is a lightweight box containing an app + everything it needs. Docker runs boxes identically on any machine. Why we care: our platform = ~8 services (database, broker, storage, our code). Without Docker, installing all that on 3 laptops identically = hell. With Docker: one file, one command.

**Learn.** Image vs container (recipe vs cake), Dockerfile (how to build your own image), volumes (data that survives container restarts), ports mapping (`-p 8000:8000`), then **Docker Compose**: one YAML declaring all services, `docker compose up`. Resource: [docker-curriculum.com](https://docker-curriculum.com/) then official [Compose quickstart](https://docs.docker.com/compose/gettingstarted/).

**Do.** 1) Run `docker run hello-world`, then run Postgres in a container and connect to it. 2) Write a Dockerfile for a tiny Python script. 3) Compose file with Postgres + your script inserting one row. Break it, read logs with `docker compose logs`, fix it.

**Self-check.** Image vs container? What's a volume for? Why does the whole team's stack behave identically? What does `ports: "8000:8000"` mean exactly?

### B2. PostgreSQL — the events database

**What.** The reference open-source relational database. Our single source of truth: every violation event ends up here.

**Learn.** You did SQL in A4 — here learn the *database side*: creating tables with types, primary keys, indexes; connecting from Python (`psycopg2`/`sqlalchemy`); what a transaction is. Resource: [postgresqltutorial.com](https://www.postgresqltutorial.com/) sections 1–4.

**Do.** Postgres in Docker; create the `violations` table you designed in A4; insert 1000 fake events from a Python script (random timestamps/cameras/types); run your 5 dashboard queries; add an index on timestamp and compare `EXPLAIN` before/after.

**Self-check.** Why a primary key? When does an index help and when is it useless? Why not store the video frames themselves in Postgres?

### B3. Kafka — the conveyor belt between services

**What.** A message broker: services drop messages onto named conveyor belts (**topics**); other services pick them up at their own pace. Why we care: it *decouples* camera ingestion from AI inference. If YOLO is slow for 2 minutes, frames wait on the belt instead of being lost; tomorrow we can plug a second consumer (e.g., an archiver) on the same belt without touching the producer.

**Learn.** Topics, producers, consumers, consumer groups, offsets (the bookmark of what you've read), partitions (parallel lanes). Understand conceptually why this beats service A calling service B directly. Resource: Confluent's free ["Kafka 101" course](https://developer.confluent.io/courses/apache-kafka/events/) (videos) — concepts 1–8 are enough.

**Do.** Kafka in Docker (use a ready single-node compose file); Python producer sending one JSON message per second (fake detection events); Python consumer printing them. Kill the consumer for a minute, restart it, observe it catch up — that's offsets working.

**Self-check.** What problem does a broker solve vs direct HTTP calls? What is a consumer group? If the consumer crashes, are messages lost — why not?
**Fallback note:** if Kafka setup resists > 2 days during the project, Redis Streams gives the same producer/consumer pattern, much simpler.

### B4. MinIO & object storage — the data lake

**What.** Object storage = a giant key→file dictionary over the network ("bucket/path/file.jpg" → bytes). No folders-on-disk logic, infinitely scalable, stores *anything*. MinIO is a free self-hosted clone of Amazon S3 — same API, so everything you learn = AWS skill. Why we care: videos and images don't belong in a database; they belong in a lake. We organize it in **bronze** (raw, untouched) / **silver** (processed) / **gold** (aggregated analytics) zones — the "medallion architecture" every data team uses.

**Learn.** Buckets, objects, why raw data stays immutable (you can always recompute silver from bronze; the reverse is impossible). Resource: MinIO docs quickstart + any short "medallion architecture" article (Databricks' glossary page is fine).

**Do.** MinIO in Docker (it has a nice web UI); from Python with `boto3`: create buckets `bronze/silver/gold`, upload a video to bronze, an extracted frame to silver, list objects, generate a download link.

**Self-check.** Object storage vs file system vs database — what goes where and why? Why keep bronze immutable? Why is learning MinIO ≈ learning S3?

### B5. Parquet — analytics file format

**What.** A file format storing tables **by column** instead of by row. Queries like "average per day" read only the columns they need → 10–50× faster and smaller than CSV. Our gold layer is Parquet.

**Learn + Do (together, 1–2 h).** Generate a 1M-row DataFrame, save as CSV and Parquet, compare file sizes and the time to compute a group-by after reading. Read about row vs columnar once — the exercise makes it obvious.

**Self-check.** Why is columnar faster for analytics but worse for "update one row"? When would you still use CSV?

### B6. Airflow — the scheduler of batch jobs

**What.** An orchestrator: you describe jobs as Python **DAGs** (graphs of tasks with dependencies: "aggregate AFTER validate"), it runs them on schedule, retries failures, shows history in a web UI. Why we care: our nightly jobs (aggregate events → gold, data-quality checks, drift report) must run themselves.

**Learn.** DAG/task/operator vocabulary, schedules, retries, and **idempotency**: a job re-run twice must not create duplicate data (design question: how?). Resource: official Airflow tutorial (docs.apache.org) — the fundamentals pages, ignore advanced features.

**Do.** Airflow in Docker (official compose file); write a DAG of 2 tasks: task 1 queries Postgres and writes a daily summary CSV, task 2 reads it and logs the row count; schedule it every 5 minutes; make task 1 fail once on purpose and watch the retry + red square in the UI.

**Self-check.** What is a DAG and why not just cron? What does idempotent mean and why is it vital for pipelines? What happens when a task fails?

### B7. Great Expectations — data quality

**What.** You declare rules about your data ("timestamp never null", "violation_type in allowed list", "confidence between 0 and 1") and it validates every batch and produces a readable report. Why we care: silent garbage data is the #1 killer of real analytics; showing you guard against it is a very senior reflex.

**Learn + Do (together, half a day).** GE quickstart on their docs; write 5 expectations on your fake violations table; poison the data on purpose (a null, an unknown class) and read the failure report.

**Self-check.** Give 3 examples of "bad data" that wouldn't crash any code but would corrupt the dashboard. Where in the pipeline should validation run?

---

## Part C — Computer vision modules

### C1. How object detection works (concepts first — 1 day)

**What.** Classification says "this image contains a helmet". **Detection** says "there are 3 people HERE, HERE, HERE; person 2 has no helmet" — boxes + classes. Modern one-shot detectors (YOLO family) do this in a single neural network pass, fast enough for video.

**Learn (this is your theory investment — take it seriously, it's PhD-interview material).**
- Convolutional networks refresher: what convolutions learn, feature maps.
- Detection specifics: bounding boxes, **IoU** (overlap measure between boxes), **NMS** (removing duplicate boxes), confidence scores.
- The metrics, deeply: **precision, recall, mAP@50, mAP@50-95** — you must be able to compute precision/recall from a tiny example by hand.
- Transfer learning / **fine-tuning**: why we start from a model pretrained on millions of images and only adapt it to PPE, instead of training from scratch (data efficiency).
- Resource: Stanford's CS231n notes (free online) for CNN foundations; Ultralytics docs "How YOLO works" pages; any good "mAP explained" article — then explain mAP to a teammate without notes.

**Self-check.** What is IoU? Walk through precision vs recall with a concrete PPE example (what does a false positive cost vs a false negative — which is worse for *safety*?). Why does fine-tuning work with only 3k images?

### C2. YOLO hands-on (half a day, needs the GPU)

**Do.**
1. Install Ultralytics; run pretrained `yolov8n` on a Pexels construction video — see boxes appear. (Verify it uses the GPU: `device=0`.)
2. Download the Roboflow Construction Site Safety dataset; look at the **data format**: images + one `.txt` per image with class/x/y/w/h — understand it by opening one file.
3. Fine-tune `yolov8n` for a few epochs; read the training curves; run `val` and interpret the mAP per class; run inference on the video again and *collect failure cases* (small persons, occlusions, weird angles).

**Self-check.** What do the numbers in a YOLO label file mean? Your no-helmet class has precision 0.9, recall 0.6 — what does that mean on a real site, and what would you try to fix it?

### C3. Tracking — from detections to *events* (half a day)

**What.** Detection is per-frame amnesia: the same worker without a helmet = 500 separate detections in 500 frames. **Tracking** links detections across frames into identities (person #7), so we can emit ONE violation event per person per episode. This detection→event logic (with debouncing: "violation only if missing for N consecutive frames") is the smartest part of our pipeline.

**Learn.** Tracking-by-detection idea; why naive box-overlap matching fails when people cross; ID switches. ByteTrack = the algorithm we use, built into Ultralytics.

**Do.** Run `model.track()` on a video with several people; draw the track IDs; watch when IDs swap (that's the hard part of tracking, be ready to discuss it). Then write 30 lines of pure Python implementing the debounce rule on a fake stream of (track_id, has_helmet) tuples.

**Self-check.** Why do we need tracking at all? What is an ID switch and what causes it? Explain your debouncing logic and its parameters.

### C4. Video plumbing: OpenCV, FFmpeg, RTSP (half a day)

**What.** OpenCV = reading/manipulating video frames in Python. FFmpeg = the Swiss-army knife CLI for video conversion/streaming. RTSP = the protocol real IP cameras speak. MediaMTX = a tiny server that turns our video files into real RTSP streams, so our platform genuinely consumes "cameras".

**Do.** Read a video with OpenCV frame by frame, save 1 frame per second as JPEG. Serve a construction video as RTSP with MediaMTX + FFmpeg, then read *the stream* from OpenCV — congratulations, you've built the project's Layer 1.

**Self-check.** What is fps and why do we process 5 fps not 30? What's a codec, roughly? Why simulate RTSP instead of just reading files directly?

---

## Part D — LLM & agent modules

### D1. LLMs locally with Ollama (half a day)

**What.** Ollama runs open LLMs (Llama, Qwen…) on your own GPU with one command and gives you an API identical to OpenAI's. Free, private, offline. **Quantization** (storing model weights in 4 bits instead of 16) is what makes an 8B-parameter model fit in your 8 GB VRAM.

**Learn.** Tokens, context window, temperature; what quantization trades away (a little quality for a lot of memory). VRAM reality: YOLO + Llama + a vision model cannot all sit in 8 GB — plan sequential loading (Ollama swaps models automatically).

**Do.** Install Ollama, `ollama run llama3.1:8b`, chat with it; then call it from Python via the API; measure tokens/second; try a 3B model and compare speed/quality.

**Self-check.** What is quantization and why do we need it? What is a context window? Why might a company prefer a local 8B model over a giant cloud API model?

### D2. Agents & tool calling with LangGraph (1 day — the fun one)

**What.** A chatbot only talks. An **agent** can *act*: the LLM decides to call tools (functions you expose: "run this SQL", "fetch this frame"), reads results, and loops until it can answer. LangGraph makes the loop an explicit graph you can debug. Our agent's job: natural language question → correct SQL on the violations DB → grounded answer.

**Learn.** Tool calling (the LLM outputs a structured function call, YOUR code executes it), agent loop (reason → act → observe → repeat), and the safety essentials: read-only DB user, validate generated SQL, force the agent to answer only from query results (anti-hallucination). Resource: LangChain Academy's free "Introduction to LangGraph" course — first modules.

**Do.** 1) A 1-tool agent: calculator. 2) The real prototype: SQLite with a fake violations table + an agent with a `run_sql` tool; ask "how many no-helmet events yesterday?" and verify the SQL it wrote. Log every SQL query the agent generates — you'll show this in the demo.

**Self-check.** Chatbot vs agent? Walk through one full loop of your text-to-SQL agent. How do you stop it from inventing numbers? Why must the DB user be read-only?

### D3. Vision-language models (2–3 h)

**What.** VLMs (like Qwen2-VL) are LLMs that also see images: give a frame + "is anyone missing a helmet?", get a text answer. We use it to *describe* flagged frames, complementing YOLO (which detects but can't explain).

**Do.** Pull a small VLM in Ollama; send it a construction photo and compare its answer with YOLO's detections; note where each one wins (YOLO: precise/fast/consistent; VLM: contextual/explanatory/slow).

**Self-check.** Why keep YOLO at all if VLMs can see? (cost, speed, consistency, measurable accuracy — know this argument, it's a great interview answer.)

---

## Part E — MLOps & serving modules

### E1. MLflow (half a day)

**What.** Two things: an **experiment tracker** (auto-records params, metrics, artifacts of every training run — compare runs in a UI) and a **model registry** (models get versions and stages; production code loads "the current production model" by name, not by file path).

**Do.** Wrap your C2 YOLO fine-tuning with MLflow logging; run 2 trainings with different epochs/image size; compare in the UI; register the best as `ppe-detector` v1; write a script that loads it *from the registry* and predicts.

**Self-check.** Why is "which exact model is deployed and how was it trained?" hard without this — and why do companies care (reproducibility, audits, rollbacks)?

### E2. FastAPI (half a day)

**What.** Python framework for building REST APIs (see A5). Ours exposes the events: `/violations`, `/stats`. Auto-generates interactive docs at `/docs` (Swagger).

**Do.** Official FastAPI tutorial first steps, then build `/violations?camera=X&limit=20` reading your fake Postgres table, with a Pydantic response model. Explore `/docs`.

**Self-check.** What does Pydantic validation buy you? What's the difference between path and query parameters? What JSON + status code does your endpoint return if the camera doesn't exist?

### E3. Streamlit dashboard (half a day)

**What.** Turns Python scripts into web dashboards — no HTML/JS. Ours shows live KPIs, latest violations with images, charts.

**Do.** A dashboard over your fake data: 3 metric cards (violations today, compliance %, active cameras), a violations-per-hour chart, a grid of the latest flagged frames, auto-refresh every 10 s.

**Self-check.** When is Streamlit the right tool vs a real frontend? What does `st.cache_data` do and why does it matter?

### E4. Drift & model monitoring (half a day — the differentiator)

**What.** Models silently rot when reality drifts from the training data (winter footage, dust on the lens, a new camera angle). **Data drift** = inputs changed. **Concept drift** = the input→output relation changed. Monitoring = tracking distributions of inputs and outputs over time and alerting on shifts. Library: **Evidently** generates drift reports comparing a reference window vs current window.

**Do.** Take detection confidences from a normal video; darken the video with FFmpeg and rerun; feed both distributions to Evidently and get the drift report. This exact scenario ("night footage degrades the model, the system notices *by itself*") is your demo's mic-drop moment.

**Self-check.** Data vs concept drift with a PPE example of each. Why doesn't accuracy monitoring work directly in production (hint: where are the labels)? What should happen automatically when drift fires?

---

## Part F — Talking about it (recruiters, M2/PhD juries)

Prepare these narratives *while* building, not the night before:

1. **The 90-second pitch.** Problem → what the system does → architecture in one breath → one number (mAP, events/sec) → one hard problem you solved. Rehearse it.
2. **The whiteboard drill.** Any member redraws the full architecture from memory and explains any arrow. Practice weekly.
3. **The "hardest problem" story.** Juries always ask. Candidates: VRAM juggling of 3 models on 8 GB; ID switches breaking violation counts; making the agent's SQL trustworthy. Document the problem, options considered, decision, result.
4. **The failure analysis.** Academically strongest section: where the detector fails (small/occluded persons, night), quantified, with hypotheses why. For a PhD/M2 audience, honest error analysis > inflated metrics. Keep a `failure_cases/` folder from day one.
5. **The "why" ladder.** For every tool, be ready for: why this tool? what's the alternative? when would the alternative be better? (e.g., Kafka vs Redis Streams vs direct calls; YOLO vs VLM; Streamlit vs React.)

---

## Suggested Phase-0 schedule (2 people, ~2 weeks)

| Day | Content |
|---|---|
| 1–2 | A1 Python + A2 terminal/WSL2 |
| 3 | A3 Git (together — do the conflict exercise as a pair) |
| 4 | A4 SQL + A5 APIs/JSON |
| 5 | B1 Docker (the keystone — don't rush it) |
| 6 | B2 Postgres + B5 Parquet |
| 7 | B3 Kafka + B4 MinIO |
| 8 | C1 detection theory (full day, both of you) |
| 9 | C2 YOLO hands-on + C4 video plumbing |
| 10 | C3 tracking + D1 Ollama |
| 11 | D2 LangGraph agent |
| 12 | E1 MLflow + E2 FastAPI |
| 13 | E3 Streamlit + E4 drift + B6 Airflow |
| 14 | B7 Great Expectations + review day: every self-check question, out loud, in pairs |

Split across 3 people some modules can run in parallel — but **A1–A5, B1, C1 are for everyone**, no exceptions: they're the shared language of the project.

---

*Companion document to `FICHE_DE_CADRAGE.md`. Tick modules off as you go — and keep your mini-exercise code in a `learning/` folder of the repo: it shows your process, which juries love.*
