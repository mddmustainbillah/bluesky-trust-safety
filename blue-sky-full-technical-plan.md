# Bluesky Trust and Safety System: Revised Production-Grade Technical Plan

## 1. Project outcome

Build a production-minded, small-scale Trust and Safety platform that:

1. consumes public Bluesky post events from Jetstream;
2. validates, buffers, and processes events reliably;
3. scores posts for spam first and toxicity second;
4. stores auditable predictions, model versions, and human labels;
5. monitors service health, data quality, model behavior, and labeled performance;
6. detects drift without confusing drift with model failure;
7. trains challenger models and promotes them through controlled quality gates;
8. deploys the complete system to AWS with reproducible containers, CI/CD, rollback,
   security controls, and cost controls;
9. adds an account-level automation-risk model only after compatible behavioral
   features and labels exist.

This is a portfolio-grade production system, not a claim to operate Bluesky-scale
moderation or make enforcement decisions for Bluesky.

---

## 2. Scope and terminology

### What the first release does

- Scores public posts for spam.
- Produces a score, a thresholded model label, and a policy decision.
- Uses the decision `allow`, `review`, or `high_risk`; it does not remove content.
- Collects human labels for offline production evaluation.
- Runs locally end to end before any AWS deployment.

### What later releases add

- Toxicity scoring as a separate post-level task.
- Account-level automation-risk scoring using behavioral aggregates.
- Guarded retraining and champion/challenger model promotion.

### Important terminology

- This is a **multi-model moderation pipeline**, not an ensemble. The models solve
  different tasks.
- **Data drift** means an input distribution changed.
- **Prediction drift** means model output distributions changed.
- **Performance degradation** means labeled quality declined.
- Drift is a proxy signal. It does not prove that a model is worse.
- Redis Streams provides **at-least-once delivery**. Duplicate delivery is expected,
  so downstream processing must be idempotent.
- `champion` is the MLflow alias for the version serving normal traffic. Do not use
  the deprecated MLflow `Production` stage.

---

## 3. Working agreement

Mustain writes the implementation.

The assistant:

- explains one concept at a time;
- gives a small, exact implementation task;
- defines acceptance criteria before code is written;
- reviews code, tests, logs, and design decisions;
- helps debug failures without replacing the learning process;
- does not move to the next phase until the current exit gate passes.

Each phase follows this loop:

1. Learn the concept.
2. Write the smallest working implementation.
3. Add unit and integration tests.
4. Exercise at least one failure path.
5. Record the decision or lesson.
6. Pass the exit gate.
7. Commit the phase.

---

## 4. Engineering principles

1. **One vertical slice first.** Complete spam ingestion, training, serving, storage,
   monitoring, evaluation, and retraining before adding toxicity.
2. **Reliability is explicit.** Document delivery guarantees, retries, timeouts,
   idempotency, retention, and recovery behavior.
3. **Offline and online features match.** Training and inference use the same versioned
   feature code.
4. **Models do not make policy alone.** A separate policy layer converts calibrated
   scores into decisions.
5. **No automatic retraining from drift alone.** Drift starts an evaluation or labeling
   workflow.
6. **No promotion based on one metric.** A challenger must pass quality, segment,
   latency, and safety gates.
7. **Privacy and deletion are system behaviors.** Deleted posts must not remain in
   the active prediction store indefinitely.
8. **Local first, AWS last.** Cloud deployment begins only after a repeatable local
   end-to-end test passes.
9. **Modular monorepo first.** Services have separate entry points and containers, but
   share contracts and libraries in one repository.
10. **Advanced infrastructure is deferred.** Kafka, Kubernetes, feature stores, model
    serving platforms, and distributed compute belong to the next-step roadmap.

---

## 5. Core tool stack

Do not add a new tool unless it solves a documented requirement that the existing
stack cannot solve reasonably.

| Layer | Tool | Responsibility |
|---|---|---|
| Runtime | Python 3.11 | Shared application and ML runtime |
| Ingestion | websockets, asyncio | Jetstream connection and event consumption |
| Contracts | Pydantic v2 | Event, configuration, request, and response validation |
| Buffer | Redis Streams | Short-retention event log and consumer groups |
| Features | pandas, NumPy, scikit-learn, langdetect | Shared offline/online feature transformations |
| Modeling | scikit-learn, LightGBM | Baselines and binary classifiers |
| Reproducibility | DVC | Dataset versions and training pipeline |
| Tracking/registry | MLflow | Runs, artifacts, signatures, versions, aliases |
| API | FastAPI, Uvicorn | Prediction, health, labeling, and internal admin APIs |
| Store | PostgreSQL, SQLAlchemy, Alembic, psycopg2 | Posts, predictions, labels, and audit metadata |
| Monitoring | prometheus-client, Prometheus, Grafana | Metrics, dashboards, and alerts |
| Drift/evaluation | Evidently | Feature, prediction, and labeled-performance reports |
| Orchestration | Prefect | Scheduled evaluation and retraining flows |
| Quality | pytest, ruff | Tests, formatting, and linting |
| Packaging | Docker, Docker Compose | Reproducible local services and images |
| CI/CD | GitHub Actions | Test, build, publish, and deploy workflows |
| Cloud | AWS | ECR, ECS Fargate, RDS, ElastiCache, S3, IAM, CloudWatch |

Necessary AWS supporting services such as an Application Load Balancer, TLS
certificate, and secret storage may be added during deployment because they solve
security and stable-endpoint requirements.

---

## 6. Target local architecture

```text
Bluesky Jetstream
        |
        v
ingestion service
  - cursor recovery
  - event parsing
  - validation
  - JSON logs/metrics
        |
        +------ invalid ------> Redis dead-letter stream
        |
        v
Redis post-event stream
  - consumer group
  - at-least-once delivery
        |
        v
spam inference worker
  - shared feature pipeline
  - champion model
  - policy thresholds
        |
        v
PostgreSQL
  - posts
  - predictions
  - labels
  - model deployment audit
        |
        +--------> Prometheus/Grafana
        |
        +--------> Evidently evaluation
                         |
                         v
                   Prefect retraining
                         |
                         v
                 MLflow challenger model
                         |
                   quality gates/review
                         |
                         v
                  champion alias update
```

FastAPI exposes synchronous prediction and internal labeling endpoints. The stream
worker is a separate process, not a FastAPI background task.

---

## 7. Revised repository structure

```text
bluesky-trust-safety/
├── src/
│   └── bluesky_trust_safety/
│       ├── common/          # settings, logging, clocks, shared errors
│       ├── contracts/       # Pydantic event, prediction, and API contracts
│       ├── ingestion/       # Jetstream connection, parsing, cursor handling
│       ├── validation/      # quality checks and dead-letter routing
│       ├── buffer/          # Redis stream writer, reader, recovery
│       ├── features/        # versioned shared feature transformations
│       ├── training/        # reusable preparation, training, evaluation logic
│       ├── policy/          # thresholds and allow/review/high-risk decisions
│       ├── serving/         # model loader, FastAPI app, stream worker
│       ├── store/           # SQLAlchemy models and repositories
│       ├── labeling/        # sampling and human-label operations
│       ├── monitoring/      # Prometheus metrics and health checks
│       ├── drift/           # reference data and Evidently reports
│       └── retraining/      # Prefect challenger and promotion flows
├── scripts/
│   ├── run_consumer.py
│   ├── run_worker.py
│   ├── train_spam.py
│   ├── train_toxicity.py
│   ├── build_spam_reference.py
│   └── smoke_test.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
├── notebooks/               # EDA only; production logic lives in src/
├── data/                    # DVC tracked where appropriate; ignored by Git
├── models/                  # local temporary artifacts; ignored by Git
├── reports/                 # evaluation reports; ignored unless curated
├── migrations/              # Alembic migrations
├── docker/
│   ├── docker-compose.yml
│   ├── prometheus.yml
│   └── grafana/provisioning/
├── configs/                 # versioned non-secret policy/model configuration
├── docs/
│   ├── architecture/
│   ├── adr/                 # short architecture decision records
│   ├── checklists/          # reusable project checklists
│   ├── phases/              # phase-by-phase learning guides
│   ├── runbooks/
│   ├── labeling-policy.md
│   └── model-cards/
├── infra/                   # repeatable AWS CLI deployment scripts
├── .github/workflows/
├── .env.example
├── .gitignore
├── alembic.ini
├── dvc.yaml
├── Dockerfile
├── Makefile
├── requirements.txt
├── requirements.lock.txt
└── README.md
```

---

# Implementation phases

## Phase 0: Recover and establish the engineering baseline

### Goal

Create a clean, repeatable development environment before business logic.

### Learn

- Python runtime isolation
- direct versus transitive dependencies
- reproducible commands
- Docker health checks
- unit versus integration tests

### Build

1. Resolve the currently deleted tracked scaffold files intentionally.
2. Pin the repository to Python 3.11 using the existing pyenv installation.
3. Create `venv` with Python 3.11 and ignore both `venv/` and `.venv/` conventions.
4. Separate human-maintained direct dependencies from the fully pinned lock file.
5. Install only dependencies required by the current phase, including Alembic for the
   planned database migration workflow. Add DVC when the training pipeline begins.
6. Create `.env.example` with safe placeholder values.
7. Use `docker compose`, not the legacy `docker-compose` command.
8. Start Redis and PostgreSQL with named volumes and health checks.
9. Add Make targets for install, lock, lint, format-check, unit tests, integration
   tests, up, down, logs, and smoke test.
10. Add pytest markers so unit tests do not require Docker.

### Tests

- A real smoke test imports the application package and validates configuration.
- Docker Compose reports Redis and PostgreSQL healthy.
- Unit tests pass without Docker.
- Integration test can ping Redis and run `SELECT 1` in PostgreSQL.

### Exit gate

From a clean terminal, documented commands create the environment, start dependencies,
run lint, and pass both test groups.

---

## Phase 1: Define contracts, configuration, and failure behavior

### Goal

Agree on data shapes and operational behavior before connecting to live traffic.

### Learn

- data contracts
- schema evolution
- dependency injection
- twelve-factor configuration
- structured logging

### Build

1. Define a versioned `JetstreamEvent` envelope containing:
   - `did`
   - `time_us`
   - `kind`
   - commit operation, collection, and record key when present
   - raw payload for dead-letter diagnosis
2. Define a versioned `PostEvent` containing:
   - event ID
   - post URI
   - author DID
   - operation: create, update, or delete
   - text when available
   - client-created timestamp
   - Jetstream timestamp
   - language declarations
   - reply metadata
   - schema version
3. Define `PredictionResult`, `PolicyDecision`, and API contracts.
4. Load environment configuration through one validated settings object.
5. Use standard Python logging with consistent JSON-compatible fields:
   `service`, `event`, `event_id`, `post_uri`, `attempt`, and `duration_ms`.
6. Write an architecture decision record explaining at-least-once processing and
   why idempotency is required.

### Tests

- Valid create, update, and delete fixtures parse.
- Unknown extra fields do not crash parsing.
- Missing required fields fail with actionable errors.
- Secrets never appear in settings serialization or logs.

### Exit gate

All later services can import the same contracts without circular imports, and fixture
tests define expected behavior for schema changes.

---

## Phase 2: Reliable Jetstream ingestion

### Goal

Consume live post events continuously and recover from connection failures without
silently creating gaps.

### Learn

- asynchronous iterators
- WebSocket lifecycle
- exponential backoff and jitter
- replay cursors
- graceful shutdown
- idempotent event handling

### Build

1. Connect to an official Jetstream instance with the post collection filter.
2. Parse commit create, update, and delete operations.
3. Derive the AT URI from DID, collection, and record key.
4. Persist the last successfully buffered `time_us` cursor.
5. On reconnect, rewind the cursor by a small configured window. Accept that this
   intentionally creates possible duplicates.
6. Add exponential backoff with jitter and a maximum delay.
7. Configure connect, receive, and shutdown timeouts.
8. Support graceful `SIGTERM`/`SIGINT` shutdown.
9. Allow a secondary official Jetstream host after repeated primary failures.
10. Expose ingestion health and reconnection metrics.

### Tests

- Parser tests use saved real fixtures, never a live network.
- A fake WebSocket disconnects mid-stream and reconnects from the expected cursor.
- Replayed duplicate events preserve the same event identity.
- Shutdown closes the socket and finishes the current write.

### Failure exercise

Disconnect the network or terminate the test server, then confirm reconnection, cursor
rewind, and duplicate-safe recovery.

### Exit gate

The consumer runs for at least 30 minutes, reconnects successfully after an induced
failure, and reports received, parsed, skipped, and reconnect counts.

---

## Phase 3: Validation, dead-letter handling, and Redis buffering

### Goal

Decouple ingestion from inference with explicit at-least-once semantics and observable
failure recovery.

### Learn

- validation versus parsing
- Redis Streams and consumer groups
- pending-entry lists
- acknowledgment timing
- poison messages
- retention and durability tradeoffs

### Build

1. Validate:
   - supported DID syntax
   - expected collection and operation
   - official text constraints for create/update records
   - timestamp parseability and reasonable future skew
   - language-list shape
   - reply-reference shape
2. Route invalid events to a Redis dead-letter stream with:
   - reason code
   - human-readable reason
   - original payload
   - source timestamp
   - failure timestamp
3. Write valid events to the main Redis Stream.
4. Store the event payload and cursor update safely in the ingestion workflow.
5. Enable Redis persistence for the local learning environment.
6. Create the consumer group idempotently.
7. Implement batch reads, acknowledgments, pending inspection, and `XAUTOCLAIM`.
8. Acknowledge only after the prediction transaction commits.
9. Track delivery count and move repeatedly failing messages to a processing
   dead-letter stream.
10. Configure retention from an estimated event rate and recovery window. Do not
    claim that `MAXLEN` guarantees no data loss.

### Tests

- Valid events round-trip through Redis.
- Invalid events enter the dead-letter stream with a reason.
- Unacknowledged events remain pending.
- An idle event can be claimed by a replacement worker.
- A poison event is retried only up to the configured limit.
- Redis restart behavior is documented and tested locally.

### Exit gate

The integration suite demonstrates successful delivery, duplicate delivery, worker
recovery, poison-message handling, and zero pending messages after successful work.

---

## Phase 4: Spam dataset audit and reproducible training

### Goal

Create a reproducible, leakage-aware spam classifier and understand the limits of
evaluating non-Bluesky data.

### Learn

- label definitions
- dataset licenses and provenance
- domain mismatch
- duplicate leakage
- sparse text modeling
- calibration and threshold selection
- DVC pipelines
- MLflow tracking and registry aliases

### Build

1. Write a spam-labeling policy before training.
2. Record dataset source, license, collection context, label meaning, and known
   limitations in a dataset card.
3. Use a public spam dataset for the initial baseline.
4. Audit:
   - class balance
   - nulls and malformed rows
   - exact and near duplicates
   - language mix
   - text-length distribution
   - train/test leakage risks
5. Deduplicate before splitting.
6. Preserve an untouched test set. Use a group-aware or time-aware split when the
   dataset supports it.
7. Build shared feature code:
   - TF-IDF text features
   - character and word counts
   - uppercase, digit, and punctuation ratios
   - URL, mention, hashtag, exclamation, and question counts
   - repeated-character signals
   - reply and language indicators when available
8. Compare a simple linear baseline against LightGBM. Do not assume the more complex
   model is better.
9. Prefer class weighting over synthetic text-feature oversampling unless an experiment
   demonstrates a benefit without leakage.
10. Track parameters, dataset version, Git commit, feature-schema version, metrics,
    artifacts, model signature, and input example in MLflow.
11. Track precision, recall, F1, PR-AUC, ROC-AUC, confusion matrix, calibration, and
    inference latency.
12. Select operating thresholds from false-positive and false-negative costs, not a
    default of `0.5`.
13. Use DVC stages for prepare, train, evaluate, and build-reference-data.
14. Register the accepted version and assign the MLflow alias `champion`.

### Tests

- Feature tests cover empty-safe ratios and crafted signal counts.
- Training and serving transformations produce identical vectors for the same input.
- A small fixture dataset can execute the complete DVC pipeline.
- A model reload predicts the same values as the model before serialization.
- Dataset split tests prevent the same normalized text from crossing train/test.

### Exit gate

`dvc repro` rebuilds the spam pipeline, MLflow contains comparable runs, the chosen
threshold is justified, and limitations on transfer to Bluesky are documented.

---

## Phase 5: Auditable PostgreSQL storage and policy decisions

### Goal

Persist posts, predictions, labels, and model metadata without coupling the schema to
exactly three classifiers.

### Learn

- normalized relational modeling
- migrations
- idempotent writes
- transactions
- uniqueness constraints
- retention and deletion

### Recommended schema

#### `posts`

- `post_uri` primary key
- `author_did`
- `text`
- `created_at`
- `received_at`
- `updated_at`
- `deleted_at`
- `source_event_id`
- `schema_version`

#### `predictions`

- UUID primary key
- `post_uri` foreign key
- `task` such as `spam`
- `score`
- `model_label`
- `policy_decision`
- `threshold`
- `model_name`
- `model_version`
- `feature_schema_version`
- `features_json`
- `inference_latency_ms`
- `worker_id`
- `scored_at`

Use an appropriate uniqueness rule so redelivery cannot create an unintended duplicate
for the same post, task, and model version.

#### `labels`

- UUID primary key
- `post_uri` foreign key
- `task`
- `label`
- `reviewer_id`
- `policy_version`
- `confidence`
- `notes`
- `labeled_at`

#### `model_deployments`

- model name and version
- alias
- deployment status
- deployment timestamp
- actor or flow run
- evaluation artifact reference
- rollback reference

### Build

1. Create SQLAlchemy 2.0 models.
2. Configure Alembic without committing secrets.
3. Generate and review the initial migration.
4. Implement transaction-scoped repositories.
5. Upsert posts safely for replayed create/update events.
6. Mark or remove deleted post text according to the retention policy.
7. Insert prediction and acknowledge Redis only after commit.
8. Keep the policy layer separate from the model:
   - lower score: `allow`
   - uncertain band: `review`
   - high score: `high_risk`
9. Version thresholds in configuration.

### Tests

- Migration works on an empty database.
- Upgrade and downgrade are tested where safe.
- Duplicate event processing does not create unintended prediction rows.
- A failed transaction leaves the Redis event unacknowledged.
- Delete events remove or redact text as designed.
- Repository queries are bounded and indexed.

### Exit gate

Replaying the same fixture batch twice produces the expected idempotent database state,
and deleted content follows the documented retention behavior.

---

## Phase 6: End-to-end spam inference

### Goal

Serve synchronous predictions and process streaming posts with the same model, feature,
policy, and result contracts.

### Learn

- application lifespan
- model caching
- readiness versus liveness
- atomic model reload
- API contracts
- worker transaction boundaries

### Build

1. Create an `InferenceEngine` that:
   - loads `models:/spam-classifier@champion`;
   - validates model signature and feature-schema compatibility;
   - caches the loaded model;
   - returns score, model version, threshold, and policy decision;
   - keeps the current model if a reload fails.
2. Create FastAPI endpoints:
   - `POST /v1/predict/spam`
   - `GET /health/live`
   - `GET /health/ready`
   - `GET /metrics`
3. Create an authenticated internal model-reload operation. It must not be an
   unauthenticated public endpoint.
4. Run the stream worker as a separate process.
5. Worker sequence:
   - read or reclaim event;
   - handle delete/update semantics;
   - compute features;
   - score;
   - apply policy;
   - commit post and prediction;
   - acknowledge the Redis entry.
6. Apply request-size limits, input validation, timeouts, and safe error responses.
7. Package API, worker, and ingestion entry points from the same versioned image where
   practical, using different commands.

### Tests

- API contract and 422 validation tests.
- Model dependency is replaced with a test double in unit tests.
- End-to-end fixture travels from Redis to PostgreSQL.
- Readiness fails if the model or required dependency is unavailable.
- Reload failure preserves the old champion in memory.
- Duplicate delivery remains idempotent.

### Exit gate

A live Jetstream post passes through Redis, receives a spam prediction, is stored once,
and appears through a repository query with the exact serving model version.

---

## Phase 7: Observability and reliability

### Goal

Make system behavior and failure visible before adding more models.

### Learn

- service-level indicators
- metric types
- histogram quantiles
- metric cardinality
- actionable alerts
- operational runbooks

### Metrics

#### Ingestion

- events received by operation
- events parsed and rejected
- WebSocket reconnect count
- cursor delay from current time
- Redis write failures

#### Buffer and worker

- consumer-group lag
- pending entries
- oldest pending age
- reclaimed entries
- retry count
- dead-letter count
- processing throughput

#### API and inference

- request count by route and status class
- request duration
- prediction count by task and decision
- model inference duration
- score distributions with intentional buckets
- currently loaded model version
- database failure count

### Build

1. Expose metrics from ingestion, API, and worker processes.
2. Use low-cardinality labels only. Never label metrics with DID, post URI, worker
   request ID, or raw exception message.
3. Configure Prometheus scraping for every process.
4. Provision Grafana datasources and dashboards from version-controlled files.
5. Create dashboards for:
   - traffic and throughput
   - queue health
   - error and retry rates
   - API and inference latency percentiles
   - score and decision distributions
   - model versions
6. Define initial service indicators and measure baselines before choosing final SLOs.
7. Write runbooks for:
   - Jetstream unavailable
   - Redis backlog growing
   - worker crash loop
   - PostgreSQL unavailable
   - MLflow model load failure
8. Ensure logs identify the event and model version without leaking unnecessary content.

### Failure exercise

Stop the worker while ingestion continues, observe backlog and alerts, restart it, and
verify recovery through `XAUTOCLAIM` and declining lag.

### Exit gate

Every intentionally induced failure is visible in a dashboard or log, has a documented
response, and recovers without unexplained data corruption.

---

## Phase 8: Human labeling and Bluesky production evaluation

### Goal

Create trustworthy Bluesky-domain ground truth before making performance or retraining
claims.

### Learn

- policy-based annotation
- sampling bias
- reviewer disagreement
- active-learning sampling
- production evaluation
- model limitations

### Build

1. Write a spam-labeling guide with positive, negative, uncertain, and edge-case
   examples.
2. Add authenticated internal endpoints or commands to:
   - fetch an unlabeled sample;
   - submit a label;
   - revise a label with audit history;
   - query labeling progress.
3. Sample from:
   - random posts;
   - the uncertain score band;
   - high-score posts;
   - drifted feature segments;
   - relevant language and reply segments.
4. Do not store more raw post text than the documented learning and evaluation purpose
   requires.
5. Maintain a frozen Bluesky evaluation set that is not added to training.
6. Evaluate:
   - precision, recall, F1, and PR-AUC;
   - false-positive rate;
   - calibration;
   - performance by language, reply status, and text-length segment;
   - performance in the uncertain policy band.
7. Create the first model card with training-domain and Bluesky-domain results shown
   separately.

### Tests

- Only authorized users can label.
- Invalid task/label combinations fail.
- Label revisions preserve history.
- Sampling does not repeatedly return already labeled rows unless requested.
- Deleted posts are excluded or redacted.

### Exit gate

A documented, reviewed Bluesky evaluation set exists and the system reports honest
domain performance without presenting public-dataset scores as live performance.

---

## Phase 9: Drift monitoring and guarded retraining

### Goal

Detect meaningful changes, evaluate labeled performance, and train a challenger without
automatically replacing a healthy model.

### Learn

- reference windows
- sample-size requirements
- statistical drift versus practical impact
- champion/challenger evaluation
- rollback
- orchestration

### Build

1. Save a versioned reference dataset created through the exact champion feature
   pipeline.
2. Use Evidently:
   - `DataDriftPreset` for selected input features;
   - prediction-value drift for the spam score;
   - `ClassificationPreset` only when true labels exist.
3. Require a minimum current-window sample before producing a drift decision.
4. Store report metadata:
   - reference dataset version
   - feature-schema version
   - model version
   - window start/end
   - row count
5. Schedule evaluation with Prefect.
6. Drift creates an alert and labeling task, not an immediate retraining deployment.
7. Refactor training into reusable tasks called by both the CLI and Prefect.
8. Train a challenger from:
   - versioned original training data;
   - reviewed recent labels;
   - a documented sampling and weighting policy.
9. Evaluate the challenger against:
   - the frozen original test set;
   - the frozen Bluesky evaluation set;
   - a recent labeled holdout not used for training.
10. Promotion gates include:
    - primary metric improvement or justified non-inferiority;
    - minimum recall;
    - maximum false-positive rate;
    - no unacceptable segment regression;
    - calibration check;
    - latency and model-size limits;
    - successful smoke test.
11. Begin with manual approval.
12. On approval:
    - record the deployment;
    - move the MLflow `champion` alias;
    - reload safely;
    - run post-deployment smoke tests.
13. Roll back by reassigning the previous champion alias and reloading.

### Failure exercises

- Challenger fails a quality gate and is rejected.
- Alias promotion succeeds but model reload fails; the old in-memory model remains.
- A promoted model fails the smoke test and is rolled back.

### Exit gate

A recorded demonstration shows drift evaluation, challenger training, gate results,
promotion or rejection, model reload, and rollback without using deprecated model stages.

---

## Phase 10: Add the toxicity task

### Goal

Prove that the platform supports another post-level policy and model without duplicating
the whole system.

### Learn

- task-specific label policies
- multi-label versus binary classification
- class imbalance
- shared platform versus task-specific logic

### Build

1. Write the toxicity policy before choosing labels.
2. Audit the Jigsaw dataset, license, label meaning, and domain mismatch.
3. Start with a clearly defined binary toxicity task. Treat multi-label categories as
   a documented later extension.
4. Reuse generic feature, tracking, serving, storage, metrics, drift, and labeling
   interfaces.
5. Train and register `toxicity-classifier@champion`.
6. Choose a toxicity-specific threshold and uncertain review band.
7. Collect and evaluate a Bluesky-domain toxicity sample.
8. Update the policy engine to combine independent signals while preserving each
   model's score and reason.

### Exit gate

Adding toxicity requires configuration and task-specific training/policy code, not a
copy of the entire spam pipeline. Both tasks are independently observable and auditable.

---

## Phase 11: Account-level automation-risk model

### Goal

Add bot-related learning only when the online feature contract can support it.

### Important boundary

Do not predict `bot` from a single post and DID. Name the output
`automation_risk` unless the labels truly establish bot identity.

### Candidate rolling features

- posts per hour/day
- median and variance of inter-post time
- repeated or near-duplicate text ratio
- URL ratio
- mention and reply ratio
- unique interaction targets
- active-hours distribution
- language consistency
- deletion/update ratio
- burstiness

### Build

1. Create rolling author aggregates from observed public events.
2. Version the aggregation window and feature definitions.
3. Audit Cresci-2017 and keep only labels/features that can be mapped legitimately to
   the online Bluesky feature contract.
4. If dataset compatibility is inadequate, stop at a rules-based research score and
   document why a supervised claim would be invalid.
5. If compatibility passes, train and evaluate an account-level model.
6. Never describe the account score as proof of malicious behavior.
7. Add author-feature drift and privacy retention controls.

### Exit gate

There is documented evidence that training and serving features match. Otherwise the
phase ends with a justified no-go decision, which is a valid production engineering
outcome.

---

## Phase 12: CI/CD and supply-chain hardening

### Goal

Make every change testable and every deployment traceable.

### Build

1. CI on pull requests:
   - install from the lock file;
   - run Ruff checks;
   - run unit tests;
   - run contract tests;
   - run selected integration tests with service containers;
   - build the production image.
2. Keep slow live-network and cloud tests outside normal unit CI.
3. Build one immutable image tagged with the Git commit SHA.
4. Do not rely on `latest` for deployment identity.
5. Generate separate commands for ingestion, API, and worker from the same image when
   dependencies are shared.
6. Add dependency and container vulnerability scanning using the chosen registry or
   GitHub security capability.
7. Protect the main branch and require successful checks.
8. Separate CI from deployment:
   - CI proves quality;
   - CD promotes an already built image.
9. Require an approval environment for the first production deployments.
10. Add a post-deployment smoke test and automatic application rollback command.

### Exit gate

A pull request cannot merge with failed quality checks, and a deployed container can be
traced to its source commit, dependency lock, migration version, and model version.

---

## Phase 13: AWS deployment

### Goal

Deploy the locally proven system with explicit networking, security, observability,
rollback, and cost controls.

### Cost gate before provisioning

1. Confirm the account's current AWS Free Plan or credit eligibility.
2. Create AWS Budgets alerts before resources.
3. Estimate monthly cost for:
   - Fargate tasks
   - Application Load Balancer
   - RDS
   - ElastiCache
   - S3
   - CloudWatch logs
   - network transfer
4. Define a teardown plan. ElastiCache and load balancers continue to cost money until
   deleted.
5. Decide how long the public demo must remain online.

### Production-shaped architecture

- ECR stores immutable images.
- ECS Fargate runs API, ingestion, worker, MLflow, and scheduled components.
- Application Load Balancer provides a stable API endpoint and health checks.
- RDS PostgreSQL stores application records and the MLflow backend.
- ElastiCache provides Redis Streams.
- S3 stores MLflow artifacts and required versioned artifacts.
- IAM task roles grant least-privilege service access.
- A managed secret store supplies database and internal API secrets.
- CloudWatch collects container logs.
- Security groups restrict RDS and Redis access to application tasks.

### Build

1. Create repeatable, reviewed AWS CLI scripts in `infra/`.
2. Create ECR repositories and lifecycle policies.
3. Configure GitHub Actions to authenticate to AWS without application access keys
   embedded in the image or repository.
4. Provision networking and least-privilege security groups.
5. Provision RDS and run Alembic as a controlled deployment task.
6. Provision ElastiCache with appropriate persistence/backup expectations documented.
7. Create the S3 artifact bucket with encryption and blocked public access.
8. Deploy the MLflow tracking server with a database-backed registry and S3 artifacts.
9. Deploy API, ingestion, and worker services.
10. Configure ALB readiness checks and TLS for any public demonstration.
11. Configure autoscaling only after measuring meaningful CPU, request, or queue-lag
    signals.
12. Send logs to CloudWatch with bounded retention.
13. Run end-to-end, restart, duplicate-delivery, model-reload, and rollback tests.
14. Teardown or scale down resources after the demo according to the cost plan.

### Exit gate

The stable HTTPS endpoint passes readiness, a live post is scored and stored, dashboards
show the AWS system, a task restart recovers safely, rollback is demonstrated, and
actual cost is compared with the estimate.

---

## Phase 14: Portfolio proof and operational review

### Goal

Demonstrate engineering judgment, not merely a list of tools.

### Final artifacts

1. README with:
   - problem and non-goals
   - architecture diagram
   - local quickstart
   - model results and limitations
   - reliability semantics
   - screenshots
   - AWS cost summary
2. Architecture decision records for:
   - Redis instead of Kafka
   - at-least-once delivery
   - modular monorepo
   - MLflow aliases
   - manual-first promotion
   - bot-model go/no-go decision
3. Model cards for spam and toxicity.
4. Dataset cards and labeling policy.
5. Operational runbooks.
6. A recorded demo showing:
   - live ingestion
   - queue and worker behavior
   - stored prediction
   - dashboards
   - induced worker failure and recovery
   - drift report
   - challenger evaluation
   - promotion/rejection
   - rollback
7. A short case study explaining tradeoffs and what would change at larger scale.

### Exit gate

Mustain can answer, with evidence:

- What happens when a worker crashes?
- How are duplicates handled?
- How are labels obtained?
- How is drift different from performance degradation?
- Why was a model promoted or rejected?
- How is a bad model rolled back?
- What happens when a post is deleted?
- How are secrets and internal endpoints protected?
- What are the system's measured latency and throughput?
- What does the AWS deployment cost?

---

## 8. Testing strategy across all phases

### Unit tests

- parsers and validators
- feature extraction
- policy thresholds
- model result mapping
- repository decision logic with test doubles

### Contract tests

- saved Jetstream event shapes
- Redis payload schema
- FastAPI request and response schema
- model signature and feature-schema compatibility

### Integration tests

- Redis Streams and recovery
- PostgreSQL transactions and migrations
- MLflow registration, aliases, and loading
- Prometheus metrics exposure

### End-to-end tests

- fixture event to stored prediction
- live event to stored prediction in a controlled smoke test
- human label to performance report
- approved challenger to model reload

### Failure tests

- WebSocket disconnect
- duplicate event
- Redis restart
- worker killed after read but before acknowledgment
- poison message
- PostgreSQL unavailable
- model load failure
- failed hot reload
- post deletion
- AWS task replacement

---

## 9. Suggested schedule

Progress is controlled by exit gates, not calendar pressure. A realistic part-time
learning schedule is:

| Weeks | Phases | Outcome |
|---|---|---|
| 1 | 0-1 | Reproducible foundation and contracts |
| 2 | 2 | Reliable Jetstream ingestion |
| 3 | 3 | Redis delivery and recovery |
| 4-5 | 4 | Reproducible spam model |
| 6 | 5-6 | Stored end-to-end inference |
| 7 | 7 | Observability and failure recovery |
| 8 | 8 | Human labels and Bluesky evaluation |
| 9 | 9 | Drift and guarded retraining |
| 10 | 10 | Toxicity task |
| 11 | 11 | Account-risk research/go-no-go gate |
| 12 | 12 | CI/CD hardening |
| 13-14 | 13 | AWS deployment and rollback |
| 15 | 14 | Documentation, case study, and demo |

If less time is available, finish Phases 0-9 deeply before adding more models. One
reliable, monitored model is stronger than three incomplete classifiers.

---

## 10. Advanced next-step roadmap

These tools are intentionally excluded from the initial implementation. Add them only
after the core system is measured, documented, and limited by a problem they solve.

### A. Kafka or Redpanda

Add when Redis retention, partitioning, replay, or consumer scaling becomes a measured
constraint.

Learn:

- partitions and ordering keys
- consumer rebalancing
- retention and replay
- schema registry and compatibility
- dead-letter topics

Migration exercise:

- introduce an event-bus interface;
- run Redis and Kafka adapters against the same contract tests;
- replay a retained topic to rebuild predictions.

### B. Kubernetes and Helm

Add after ECS deployment works and there is a clear need to learn cluster operations.

Learn:

- deployments, services, jobs, and CronJobs
- readiness/liveness probes
- resource requests and limits
- secrets and configuration
- horizontal autoscaling
- rolling updates

Do not use Kubernetes merely to replace a working Docker Compose environment.

### C. KServe or Seldon

Add after Kubernetes and the custom inference engine are understood.

Learn:

- standardized model serving
- canary rollout
- inference graphs
- autoscaling and model revisions

Compare the platform with the existing FastAPI implementation and document the
operational tradeoff.

### D. Feature store such as Feast

Add when the account-level model creates a genuine offline/online aggregation problem.

Learn:

- feature definitions
- point-in-time correctness
- offline and online stores
- feature freshness
- materialization

Do not add a feature store for static TF-IDF text features.

### E. Transformer and multilingual models

Add after the classical baselines and Bluesky evaluation set exist.

Candidates:

- compact transformer toxicity classifier
- multilingual text encoder
- distilled model for CPU inference

Compare accuracy, calibration, latency, memory, image size, and cloud cost against the
classical champion.

### F. Infrastructure as code

Replace or complement AWS CLI scripts with Terraform or AWS CDK after the manual AWS
resource relationships are understood.

Learn:

- state
- plans
- modules
- environment separation
- drift detection
- safe teardown

### G. OpenTelemetry and distributed tracing

Add when debugging a post across ingestion, Redis, worker, database, and API from logs
and metrics becomes difficult.

### H. Large-scale data processing

Use Dask or Spark only when measured batch volume makes pandas inadequate. Document
the dataset size and runtime evidence that justified the change.

### I. Advanced deployment patterns

- shadow evaluation
- canary traffic
- automated rollback
- multi-region ingestion
- disaster recovery
- load-based worker autoscaling
- policy experimentation

---

## 11. Definition of complete

The initial project is complete when:

- spam works end to end on live Jetstream events;
- toxicity uses the same reusable platform;
- the account-risk phase has either a valid model or a documented no-go decision;
- delivery, retry, duplicate, deletion, and rollback behavior are tested;
- training is reproducible with DVC;
- experiments and champion aliases are managed in MLflow;
- human labels support honest Bluesky-domain evaluation;
- drift and labeled performance are reported separately;
- retraining produces a challenger and uses guarded promotion;
- dashboards and runbooks cover important failures;
- CI creates a traceable immutable image;
- AWS deployment is secure, observable, reproducible, and cost-measured;
- the documentation states limitations without overstating production scale or model
  certainty.
