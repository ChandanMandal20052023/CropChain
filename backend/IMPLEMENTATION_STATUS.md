# CropChain Backend Implementation Audit

> Initial audit of the backend implemented before continuing with Version 1
> functionality. This document is located inside `backend/` and reflects the
> state of the repository at the start of this implementation campaign.

---

## 1. Existing implementation

| Area | Existing state |
|---|---|
| Accounts | Custom email-based `User` model, JWT auth via `djangorestframework-simplejwt`, registration/login/refresh/logout/me/password/roles/admin-user APIs. |
| Farms | `Farm` model, farm CRUD API with ownership verification, geolocation, acreage validation and `farm_code` generation. |
| Batches | `Batch` model, batch CRUD API with unique `batch_code`, crop, quantity, dates, lifecycle state machine and filtering. |
| Traceability | No models, views or API endpoints implemented. |
| Quality | No models, views or API endpoints implemented. |
| Blockchain / Fabric | Directory scaffolding only (`*.gitkeep`). Adapter, transaction status, ledger queries and transaction tracking not implemented. |
| Public portal | No models, views or API endpoints implemented. |
| Audit | `AuditLog` model exists but no manager helper, no users-facing API, no permissions. |

---

## 2. Completed functionality

- Custom email-based `User` model with role choices: `admin`, `farmer`, `supplier`, `warehouse`, `transporter`, `processor`, `inspector`, `retailer`, `consumer`.
- JWT authentication (access + refresh), token rotation, blacklist, last-login tracking.
- Registration, login, logout, current-user profile, password change, roles listing, and admin user listing/detail/deactivation.
- Farm registration and listing with owner validation, verification status and geolocation/acreage handling.
- Batch creation and listing with unique server-generated `batch_code`, crop, variety, quantity, unit, dates, lifecycle status and filtering/search/pagination.
- Audit `AuditLog` model and basic `audit/` admin-only read endpoints behind `IsAuditAdmin`.

---

## 3. Partially implemented functionality

- **Traceability / milestones**: endpoint skeleton exists but no milestone events, stage-transition validation or Fabric event anchoring are implemented.
- **Quality / certificates**: model and API skeleton exist, but file-upload validation, SHA-256 hashing, file-size limits and hash verification are not implemented.
- **Audit API for writes**: `AuditLog.objects.log()` was added to support auditable operations; broader audit capture for every business operation was not completed system-wide.
- **Public portal / QR**: `BatchToken` model and public tracking endpoint were added; the full passport, QR payload and public serialization requirements are not complete.
- **Blockchain / Fabric**: adapter, transaction status, and ledger integration were not present. Production Fabric SDK wiring remains a documented external dependency.

---

## 4. Missing functionality

Implemented in this campaign:

- Traceability milestone events with stage-transition validation, actor/organization resolution, chronological history and Fabric transaction linkage.
- Quality inspection and certificate model, upload validation, SHA-256 generation, hash verification and public/private field separation.
- Public batch passport with a tokenized tracking endpoint and explicit `verified`/`pending`/`failed` rendering.
- Fabric adapter interface, production/test adapter modes, transaction persistence, retry/idempotency, and transaction submission + status/query endpoints.
- Audit log manager helper and audit-writable API coverage for the core operations.
- New migrations for `audit`, `blockchain`, `public_portal`, `quality` and `traceability`.
- Tests and full migration/test pipeline: `check`, `makemigrations --check --dry-run`, `migrate`, `test`.

---

## 5. Bugs and security concerns

- **App registration mismatch**: the original `INSTALLED_APPS` referenced `apps.traceability`, `apps.quality`, etc., while `apps.py` used non-dotted names, and `config.urls` required `apps.*.urls`. This was resolved by aligning all app labels, adding missing `urls.py` files and ensuring `manage.py` puts the project root on `sys.path`.
- **Mangled existing models**: rewriting audit/quality/traceability models risked duplicating `Batch.Unit` choices. `Batch.Unit` was sourced from the existing `apps.batches.models.Batch`, avoiding a conflicting duplicate definition.
- **Public API boundary**: the public tracking endpoint enforces strict field whitelisting and never exposes exact coordinates, internal `created_by` identity, private notes or storage paths.
- **Audit sensitivity**: the audit manager avoids storing passwords, tokens, private keys or uploaded file bytes.

---

## 6. Required implementation steps (in this campaign)

1. **Foundation** — Fix app registration and settings so all `apps.*` modules import.
2. **Traceability** — Milestone events, allowed stage transitions, actor/org resolution, persistence, authentication and chronological history.
3. **Quality** — Certificate upload, SHA-256, hash verification, public/private field separation.
4. **Public portal** — Tokenized public passport, QR-ready payload, `verified`/`pending`/`failed` rendering.
5. **Blockchain** — Fabric adapter interface, transaction persistence (`PENDING`/`CONFIRMED`/`FAILED`), submission, status query and history.
6. **Audit** — `AuditLog.objects.log()` helper, admin-only read API, and coverage of core operations.
7. **Final validation** — Migrations, `check`, `makemigrations --check --dry-run`, `test`.

---

## 7. External dependencies / blockers

- **Hyperledger Fabric 3.1 network and Go chaincode**: the adapter interface is fully implemented, but the real Fabric Gateway SDK integration is blocked on an operational network, credentials and the exact chaincode function names. Until then the adapter refuses to fabricate results and reports a clean `FabricModeDisabledError` path.
- **MySQL 8.0**: the project default database remains SQLite for local development. A `db.sqlite3` database is used by migrations and tests; production must point `DATABASES` at MySQL.
- **QR code generation**: `qrcode` and Pillow are present in `requirements.txt`, but runtime QR rendering against the public passport endpoint is not part of the Django API contract and is left to the frontend.

---

## 8. Recommended execution order (already followed)

1. Audit the existing backend and register all apps.
2. Implement traceability events and stage transitions.
3. Implement quality certificates and hash verification.
4. Implement the public portal passport.
5. Implement Fabric adapter and transaction tracking.
6. Complete audit logging and security.
7. Run `check`, `makemigrations --check --dry-run`, `migrate`, `test`.
