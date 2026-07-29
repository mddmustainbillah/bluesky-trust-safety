# Project Brief: Bluesky Trust and Safety System

## What this project is

A production-minded Trust and Safety platform that consumes public Bluesky post events
from the Jetstream WebSocket service, evaluates them through a multi-model moderation
pipeline, and records auditable predictions and human labels.

The system begins with spam detection as one complete vertical slice. After ingestion,
buffering, training, serving, storage, monitoring, evaluation, and retraining work for
spam, the platform adds toxicity detection. Account-level automation-risk detection is
added only if compatible behavioral features and labels can be built legitimately.

The system makes `allow`, `review`, or `high_risk` recommendations. It does not remove
content or claim to operate moderation for Bluesky.

## Who this is for

Md Mustain Billah (Mustain), AI/ML Engineer at ITL Group, Dhaka, Bangladesh.

Background:

- about three years of AI/ML engineering experience;
- LLM pipelines, FastAPI, Docker, MLflow, Prefect, Dask, DVC;
- recommendation systems and CI/CD.

Career objective:

- develop production MLOps and ML-system-design depth;
- build a differentiated flagship portfolio project;
- prepare for MLOps and ML platform roles at product technology companies.

## Why this project

- Trust and Safety is a real ML platform problem involving policy, data, models,
  reliability, monitoring, and human feedback.
- Bluesky Jetstream provides a real public event stream with no application
  authentication required for the public instances.
- A streaming supervised-learning system demonstrates more engineering depth than a
  static notebook or isolated prediction API.
- The project can show delivery semantics, model governance, human labeling, drift,
  retraining, rollback, CI/CD, and cloud operations in one coherent system.
- Building one vertical slice and then adding tasks demonstrates reusable platform
  design instead of collecting disconnected tools.

## Honest scope

This is a portfolio-grade, production-minded small-scale system.

It is not:

- a claim to ingest or moderate all Bluesky traffic with platform-level guarantees;
- a fully autonomous enforcement system;
- proof that public-dataset performance transfers directly to Bluesky;
- proof that an account is malicious merely because it receives a high automation-risk
  score.

## Core architecture

```text
Bluesky Jetstream
        |
        v
ingestion + validation
        |
        +---- invalid events ----> dead-letter stream
        |
        v
Redis Streams
        |
        v
inference worker
        |
        +---- shared feature pipeline + MLflow champion model
        |
        v
PostgreSQL posts, predictions, labels, and deployment audit
        |
        +----> Prometheus and Grafana
        |
        +----> Evidently evaluation
                       |
                       v
              Prefect challenger training
                       |
                 guarded promotion
                       |
                       v
                MLflow champion alias
```

FastAPI provides synchronous prediction, health, metrics, and authenticated internal
labeling/admin operations. The stream worker runs as a separate process.

## Core tool stack

| Layer | Tools | Job |
|---|---|---|
| Runtime | Python 3.11 | Shared application and ML runtime |
| Ingestion | websockets, asyncio, Pydantic | Jetstream connection and event contracts |
| Validation | Pydantic validators, dead-letter stream | Reject, explain, and retain invalid events |
| Buffer | Redis Streams | Short-retention, at-least-once event processing |
| Features | pandas, NumPy, scikit-learn, langdetect | Shared offline/online transformations |
| Modeling | scikit-learn, LightGBM | Baselines and classifiers |
| Reproducibility | DVC | Dataset and training-pipeline versions |
| Tracking/registry | MLflow | Runs, artifacts, signatures, versions, champion alias |
| Serving | FastAPI, Uvicorn | Prediction and internal operational APIs |
| Store | PostgreSQL, SQLAlchemy, Alembic, psycopg2 | Posts, predictions, labels, audit history |
| Monitoring | prometheus-client, Prometheus, Grafana | Metrics, dashboards, and alerts |
| Evaluation | Evidently | Data, prediction, and labeled-performance reports |
| Orchestration | Prefect | Scheduled evaluation and challenger training |
| Quality | pytest, ruff | Tests, formatting, and linting |
| Packaging | Docker, Docker Compose | Local services and production images |
| CI/CD | GitHub Actions | Test, build, publish, deploy, and smoke test |
| Cloud | AWS | ECR, ECS Fargate, RDS, ElastiCache, S3, IAM, CloudWatch |

## Critical design decisions

### One vertical slice first

Complete spam end to end before adding toxicity. Complete the post-level platform before
attempting account-level automation-risk modeling.

### Multi-model pipeline, not ensemble

Spam, toxicity, and automation risk are different tasks. A separate policy layer
combines their independent scores into review decisions.

### Redis semantics

Redis Streams provides at-least-once delivery, not exactly-once processing and not an
unqualified no-data-loss guarantee. The worker uses idempotent database writes,
acknowledges only after commit, reclaims abandoned messages, and dead-letters poison
messages.

### DVC and Prefect

- DVC makes datasets and training steps reproducible.
- Prefect schedules evaluation and challenger-training workflows.
- Prefect may call reusable training/DVC operations, but the two tools solve different
  problems.

### Drift and retraining

Input or prediction drift is a warning signal. It triggers investigation and targeted
labeling. It does not automatically prove performance degradation or justify deploying
a new model.

Retraining:

1. uses reviewed labels;
2. creates a challenger;
3. evaluates frozen and recent holdouts;
4. checks quality, segments, calibration, and latency;
5. begins with manual approval;
6. moves the MLflow `champion` alias only after passing gates;
7. supports rollback to the previous champion.

### Human labels

The prediction store includes a real labeling workflow, label policy, reviewer
metadata, uncertainty, and audit history. Automated retraining is not claimed until
enough trustworthy labels exist.

### Bot detection boundary

Bot or automation-risk detection is an account-level problem. It requires rolling
behavioral features such as posting rate, burstiness, repeated content, URL ratio,
interaction diversity, and active-hour patterns. The project will not infer bot status
from a single post and DID.

### Local first, AWS last

The full spam vertical slice, monitoring, failure recovery, labeling, and retraining
must work locally before AWS provisioning begins.

### No premature infrastructure

Kafka/Redpanda, Kubernetes, KServe/Seldon, a feature store, transformer models,
Terraform/CDK, OpenTelemetry, and distributed batch compute are reserved for the
advanced next-step roadmap. Each requires a measured problem or a deliberate learning
objective.

## Revised phases

0. Recover and establish the engineering baseline.
1. Define contracts, configuration, and failure behavior.
2. Build reliable Jetstream ingestion with cursor recovery.
3. Add validation, dead-letter handling, and Redis buffering.
4. Audit data and train the reproducible spam model.
5. Add auditable PostgreSQL storage and policy decisions.
6. Complete end-to-end spam inference.
7. Add observability, runbooks, and failure recovery.
8. Build human labeling and Bluesky-domain evaluation.
9. Add drift monitoring and guarded champion/challenger retraining.
10. Add toxicity using the reusable platform.
11. Research and gate the account-level automation-risk model.
12. Harden CI/CD and the container supply chain.
13. Deploy to AWS with security, rollback, and cost controls.
14. Produce the architecture case study, model cards, runbooks, and recorded demo.

See `blue-sky-full-technical-plan.md` for implementation steps, tests, failure
exercises, and exit gates.

## Working style

- Mustain writes the implementation.
- The assistant teaches concepts, assigns small tasks, reviews code, and helps debug.
- Work proceeds one phase and one exit gate at a time.
- A phase is not complete because files exist; its success and failure paths must be
  demonstrated.
- Reliability and model limitations are documented as the project evolves.

## Initial definition of success

The strongest first release is:

- one spam model working end to end;
- real Jetstream events processed with duplicate-safe recovery;
- predictions stored with exact model and feature versions;
- dashboards showing health, errors, queue lag, latency, and score behavior;
- a labeled Bluesky evaluation set;
- drift reported separately from performance;
- a challenger promoted or rejected through documented gates;
- a demonstrated rollback;
- repeatable local setup and green CI.

One deeply completed model is more valuable than three incomplete classifiers.

## Advanced next step

After the initial project is complete, expand deliberately:

1. Kafka or Redpanda for longer retention, partitions, and replay.
2. Kubernetes and Helm for cluster operations.
3. KServe or Seldon for standardized serving and canary rollouts.
4. Feast when account features create a genuine offline/online feature problem.
5. Transformer and multilingual models with latency/cost comparisons.
6. Terraform or AWS CDK for infrastructure as code.
7. OpenTelemetry for cross-service traces.
8. Dask or Spark only when measured batch volume exceeds pandas.
9. Shadow traffic, canary deployment, autoscaling, multi-region, and disaster recovery.

## Final portfolio evidence

- Live GitHub repository with green CI.
- Reproducible DVC and MLflow experiments.
- Architecture diagram and decision records.
- Model cards and dataset cards.
- Grafana dashboards and operational runbooks.
- Recorded failure-recovery and model-rollback demo.
- Written case study with measured latency, throughput, model quality, limitations,
  AWS architecture, and actual cost.
- Public API demonstration that does not expose internal label or reload operations.
