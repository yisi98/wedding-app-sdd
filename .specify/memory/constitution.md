<!--
SYNC IMPACT REPORT
==================
Version change: 1.0.0 → 1.1.0
Bump rationale: MINOR. Principle IV's mandated feature set is materially narrowed —
  share links are descoped by explicit couple decision — and the test-coverage quality
  bar is corrected to the verified suite size. No principle is removed or redefined.
Modified principles:
  - IV. Full-Featured, Not MVP — "sharing" removed from the mandated feature list;
    descope of share links recorded below with rationale.
Modified sections:
  - Quality Bars & Additional Constraints — integration-test baseline corrected from
    119 (aspirational, never achieved) to the verified 97 passing tests.
Added sections:
  - Amendment Log
Removed sections: none
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ compatible (Constitution Check gate is generic)
  - .specify/templates/spec-template.md ✅ compatible (WHAT/WHY sections unaffected)
  - .specify/templates/tasks-template.md ✅ compatible
Downstream artifacts updated in the same change:
  - specs/001-wedding-media-platform/spec.md (US5, FR-020, FR-021, Share Link entity)
  - specs/001-wedding-media-platform/plan.md (Constitution Check row IV, test baseline)
  - specs/001-wedding-media-platform/tasks.md (Phase 7 removed; T069/T086 reopened)
  - specs/001-wedding-media-platform/contracts/share.md (deleted)
  - specs/001-wedding-media-platform/data-model.md (share_links table + relationships)
  - specs/001-wedding-media-platform/quickstart.md (share validation step)
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
social engagement, real-time, notifications, PWA, admin, bulk operations). Scope
reduction is NOT the default response to schedule pressure; features are descoped only
by explicit couple decision, documented as a constitution amendment. **Rationale**: The
couple explicitly chose completeness over a minimal product; this is a one-time,
non-repeatable event.

**Descoped by amendment**: *Share links* (public tokenised links to the gallery or a
single item, with QR code, access counting and optional expiry) were removed from the
mandated set on 2026-08-17. Content stays reachable only behind the shared event
password, which is the behaviour Principle III wants anyway; guests who want to pass
media on use the bulk-download archive instead. See the Amendment Log.

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
  suite MUST remain green and MUST NOT shrink (baseline: **97 passing integration
  tests**, verified 2026-08-17). The earlier figure of 119 was an estimate recorded at
  ratification and never matched a real run; it is corrected here rather than carried
  forward as a false gate.
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

## Amendment Log

### 1.1.0 — 2026-08-17 — Descope share links; correct the test baseline

**Principle IV.** Share links are removed from the mandated feature set.

*Decision*: taken by the couple. *Rationale*: the feature was implemented and then
removed from the codebase during development; with the 2026-09-15 deployment deadline
29 days out, rebuilding it competes with the go-live gates that Principle VII protects.
Tokenised public links also sit in tension with Principle III, which requires all
content to stay behind the shared event password. Guests who want to pass media on can
use the bulk-download archive (FR-035), which is unaffected.

*Migration impact*: `share_links` was already dropped by migration `0005_drop_share_links`;
no further schema change is required. FR-020 and FR-021 are withdrawn and their
identifiers retired rather than reused, so existing references stay unambiguous. User
Story 5 is withdrawn; US6–US9 keep their numbers for the same reason.

**Quality bars.** The integration-test baseline is corrected from 119 to the verified 97.

**Version**: 1.1.0 | **Ratified**: 2026-07-04 | **Last Amended**: 2026-08-17
