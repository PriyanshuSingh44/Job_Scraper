# DECISIONS.md

Three questions I need to answer directly about how and why I built this the way I did.

---

## 1. Why this ingestion strategy over the alternatives?

**What I chose**: Scheduled polling of two open public APIs — Remotive as the primary
source, Arbeitnow as an automatic fallback — with retry, circuit-breaker, and schema
validation layered on top.

**What I rejected**: Headless-browser scraping of a JS-heavy site like LinkedIn or Indeed.

**Why I made that call**:

The brief is asking me to demonstrate resilience thinking — how a pipeline handles
failure, drift, and source unreliability. That's a systems design question, not a
"can you get around bot detection" question. I can show circuit-breaker logic, retry
with backoff, and automatic fallback just as clearly against a real open API as I can
against a hostile scraping target. The difference is that the open API route doesn't
burn time on playwright-stealth, proxy rotation, and fingerprint spoofing — time I'd
rather spend on the actual resilience architecture that the rubric is grading.

There's also an honest ethical reason: hitting LinkedIn or Indeed with an automated
client, even for a demo, is adversarial against a site that's explicitly said no. I
don't want to build a demo I can't stand behind. Remotive and Arbeitnow are public
APIs designed to be consumed programmatically — this is exactly their intended use.

---

## 2. One trade-off I made under time pressure

**The trade-off**: SQLite instead of PostgreSQL, and I described proxy rotation
conceptually in the design doc rather than implementing it for real.

With a real week I'd do two things differently:

First, I'd swap SQLite for a managed PostgreSQL instance (Render has a free tier).
SQLite is single-writer — fine for a single-replica demo, but it breaks the moment
you scale horizontally. The SQLAlchemy abstraction means the swap is about 10 lines
of config change, but I'd want to actually run it in production with proper connection
pooling via `asyncpg` before calling it done.

Second, I'd implement a real proxy pool rather than just describing one. The current
pipeline runs from a datacenter IP, which is fine for Remotive but would be flagged
immediately by any anti-bot system. With more time I'd integrate `curl_cffi` for
Chrome-matching TLS fingerprints and a residential proxy provider so the resilience
story holds against a genuinely hostile target, not just a friendly API.

---

## 3. Where I used AI, and where I didn't

I used AI assistance to:
- Think through the circuit-breaker state machine at a conceptual level — specifically
  whether the breaker should reset on first success or require N consecutive successes
  (I landed on first success, explained below)
- Scaffold the FastAPI router boilerplate — the `include_router` wiring, lifespan
  context manager pattern, and CORS middleware setup
- Get a quick second opinion on the retry decorator signature shape before writing it

I wrote personally without AI scaffolding:
- The retry backoff logic in `app/resilience/retry.py` — the exponential formula,
  the `last_exc` carry-through across attempts, and the `max_attempts` loop structure
- The circuit breaker state logic in `circuit_breaker.py` — specifically the
  `record_failure` / `record_success` split and why I chose a singleton over
  dependency injection for this use case
- The full pipeline orchestrator in `pipeline.py` — the source-selection branch,
  empty-response detection, the validate-then-normalize order, upsert deduplication,
  and the log-write on every outcome including partial drift
- The validator in `ingestion/validator.py` — the required-fields contract per source,
  and the distinction between "key missing" (schema drift) vs "key present but empty"
  (data quality issue)

**On the circuit breaker reset decision specifically**: I chose reset-on-first-success
rather than reset-after-N-successes because the goal is to restore the primary source
as quickly as possible once it's back. If the primary returns valid data once, that's
sufficient evidence it's healthy — requiring N consecutive successes would mean I'm
unnecessarily penalizing a recovered source and pulling from the fallback longer than
I need to. I can defend this in a call if asked.
