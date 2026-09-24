# Violation Event Contract — v1

The canonical shape of a violation, as enforced by `database/init/001_schema.sql`
and validated at the API layer by `ViolationCreate` in `src/api/main.py`.

## Fields

| Field | Type | Constraint | Source |
|---|---|---|---|
| id | integer | primary key, auto-assigned | database |
| camera_id | integer | required, must reference an existing camera (foreign key) | database + API |
| track_id | integer | optional (populated starting Week 2, ByteTrack) | database |
| violation_type | text | required | database + API |
| confidence | float | required, 0.0 to 1.0 inclusive | database (CHECK) + API (Pydantic Field) |
| started_at | timestamp | required | database + API |
| ended_at | timestamp | optional (populated once debouncing lands, Week 2) | database |
| evidence_uri | text | optional (populated once evidence storage lands, Week 3) | database |

## Validation layers (defense in depth)

1. **Pydantic** (`ViolationCreate`, API layer) — rejects malformed requests immediately,
   before touching the database. Returns HTTP 422 with a precise error.
2. **PostgreSQL constraints** (`CHECK`, `NOT NULL`, `FOREIGN KEY`) — the database's own,
   unconditional guarantee, regardless of what's writing to it.

## Known limitation (v1)

A foreign key violation (e.g. `camera_id` referencing a non-existent camera) currently
surfaces as an unhandled HTTP 500 from the API, rather than a clean 4xx error. This is
acceptable for now but should be caught and returned as a proper validation error in a
future iteration.

## Versioning rule

Any change to a field's name, type, or required/optional status is a breaking change
and must be released as v2, documented here, with all downstream consumers
(ingestion, agent, dashboard) updated deliberately — never a silent change to v1.
