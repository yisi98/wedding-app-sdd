<!--
SYNC IMPACT REPORT
==================
Version change: (none) → 1.0.0
Bump rationale: Initial ratification of the project constitution (MAJOR baseline).
Modified principles: n/a (initial adoption)
Added sections:
  - Core Principles (I–VII)
  - Quality Bars & Additional Constraints
  - Development Workflow & Deadline Governance
  - Governance
Removed sections: none
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ compatible (Constitution Check gate is generic; principles map cleanly)
  - .specify/templates/spec-template.md ✅ compatible (WHAT/WHY sections unaffected)
  - .specify/templates/tasks-template.md ✅ compatible (test-per-endpoint & i18n parity captured as task types)
Follow-up TODOs: none
-->

# Wedding Media Platform Constitution

A private, password-protected web application for collecting and sharing photos and
videos from a single wedding (~150 guests), with real-time engagement, PWA support,
and a trilingual UI (English / 中文 / Русский). Deployed on AliCloud for reliable
mainland-China access.

## Core Principles

### I. China-First Infrastructure

The platform MUST run without any dependency on services blocked or unreliable in
mainland China. No Google, Facebook, or AWS services; no external CDNs; fonts are
self-hosted. Object storage MUST be S3-compatible and China-resident (AliCloud OSS in
production, MinIO in development). ICP filing MUST be completed and active before
go-live. **Rationale**: Every guest is expected to access the site from within
mainland China; a single blocked dependency can make the entire experience fail during
the event.

### II. Frictionless Guest Access

Onboarding MUST consist of exactly two inputs: a chosen display name and the single
shared event password. There MUST be no email collection, no per-user password, and no
separate registration step. First login with a new display name auto-creates the
account (get-or-create); re-entering the same name returns the same account. **Rationale**:
Guests are non-technical, on their phones, and at a live event — any added step
measurably reduces participation.

### III. Privacy by Default

All content MUST be reachable only behind the shared event password. The site MUST NOT
be publicly indexable. Secrets — event-password hash, JWT signing secret, VAPID keys,
SMTP credentials — MUST live only in environment configuration (`.env`) and MUST NEVER
be committed to version control. **Rationale**: The couple is sharing private moments
with a closed guest list, not publishing to the open web.

### IV. Full-Featured, Not MVP

The platform MUST deliver the complete agreed feature set (auth, upload, gallery,
social engagement, sharing, real-time, notifications, PWA, admin, bulk operations).
Scope reduction is NOT the default response to schedule pressure; features are
descoped only by explicit couple decision, documented as a constitution amendment.
**Rationale**: The couple explicitly chose completeness over a minimal product; this is
a one-time, non-repeatable event.

### V. Mobile-First & Offline-Tolerant

The UI MUST be designed mobile-first. PWA installability, a service worker with offline
caching, and LQIP (low-quality image placeholder) blur-up loading are REQUIRED, not
optional. **Rationale**: Most guests use phones on venue wifi that is congested and
patchy; the experience MUST degrade gracefully rather than break.

### VI. Deduplication & Integrity

Every media file MUST be content-addressed by a SHA-256 hash that is unique across the
system. Upload attempts whose hash already exists MUST be reported as duplicates and
MUST NOT be re-stored. **Rationale**: Guests routinely upload the same shared photos;
deduplication protects storage cost and keeps the gallery clean.

### VII. Hard-Deadline Discipline

All code MUST be deployed and smoke-tested in production no later than **2026-09-15**.
The wedding is **2026-10-10**; the buffer is intentional and MUST be protected.
Work MUST be prioritized to keep the production deployment continuously shippable.
**Rationale**: The deadline is externally fixed and cannot slip; a late platform has
zero value.

## Quality Bars & Additional Constraints

- **Test coverage**: Every API endpoint MUST be covered by an integration test. The
  suite MUST remain green (baseline: 119 passing integration tests).
- **Load**: The system MUST sustain 150 concurrent users without visible degradation.
  A load test MUST pass before go-live.
- **Language parity**: Every user-facing string MUST have full parity across English,
  中文, and Русский. Shipping a string in fewer than all three languages is a defect.
- **Secrets hygiene**: CI and code review MUST verify that no secret is present in the
  repository.

## Development Workflow & Deadline Governance

- Work follows Spec-Driven Development: specification → plan → tasks → implementation,
  with artifacts tracked under `specs/`.
- Changes MUST keep the production deployment shippable; long-lived broken states on the
  mainline are not permitted as the 2026-09-15 deadline approaches.
- Every pull request MUST keep the integration suite green and MUST preserve EN/ZH/RU
  string parity.
- Performance- or China-access-affecting changes MUST be validated against Principles I
  and V before merge.

## Governance

This constitution supersedes ad-hoc practices for the Wedding Media Platform. Amendments
MUST be proposed as a documented change to this file, including rationale and any
migration impact, and MUST update the version and dates below.

Versioning follows semantic versioning:

- **MAJOR**: Backward-incompatible removal or redefinition of a principle.
- **MINOR**: A new principle or section, or materially expanded guidance.
- **PATCH**: Clarifications and wording fixes with no change in obligations.

Compliance is reviewed at every pull request. Any deviation from a principle MUST be
justified in the plan's Complexity Tracking section or the amendment MUST be made first.

**Version**: 1.0.0 | **Ratified**: 2026-07-04 | **Last Amended**: 2026-07-04
