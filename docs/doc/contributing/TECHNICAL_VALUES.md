# Technical Values & Development Principles 📊

Welcome! This document outlines the core technical values, architectural decisions, and development principles that guide the engineering efforts on the **Survey Designer** project. 

By aligning on these values, we ensure that our codebase remains robust, secure, compliant, and highly maintainable, allowing our distributed team of contributors to collaborate seamlessly.

---

## 🏛️ 1. Core Architectural Pillars

Survey Designer is built around a modern, scalable, and decoupled architecture designed to deliver a fast, reliable, and user-friendly experience in the field.

```mermaid
graph TD
    subgraph Client-Side (Local Runtime)
        React[ReactJS + Vite SPA]
        I18n[i18next locales]
    end

    subgraph Service-Side (Docker Containerized)
        Backend[Django Backend]
        Worker[RQ Worker]
        DB[(PostgreSQL)]
        Cache[(Redis Cache)]
        Storage[(MinIO Storage)]
        Auth[Keycloak IDP]
        Mail[Maildev SMTP]
    end

    subgraph Build-Time Tooling
        TransCLI[translationcli.py + deep_translator]
    end

    React <-->|REST APIs / JSON| Backend
    React --> I18n
    Backend <--> DB
    Backend <--> Cache
    Backend <--> Storage
    Backend <-->|OIDC| Auth
    Backend <--> Mail
    Worker <--> Cache
    Auth <--> DB
    TransCLI -->|generates locale JSON| I18n
```

### Decoupled Architecture
* **Strict Separation of Concerns:** The frontend (**ReactJS**) and backend (**Django**) are fully decoupled. They communicate exclusively via standardized, versioned RESTful APIs.
* **Independent Runtimes:** The frontend runs as a Single Page Application (SPA) in the user's browser, while the backend is an API provider and task executor running inside containerized services.

### Monorepo Approach
* **Single Source of Truth:** Both the frontend (`react-ui`) and backend (`dj-be`) reside in a single repository. This enables atomic commits across layers, facilitates co-dependent changes, and simplifies repository discovery.
* **Unified Tooling & Guidelines:** All documentation, licensing, security protocols, and shared developer environments are consolidated, simplifying onboarding and ensuring compliance.

### Full Service Topology
The backend stack is orchestrated by `dj-be/docker-compose.yml`. Each service
has a distinct responsibility and a documented reason for being part of the
architecture.

| Service | Image / Tech | Local Port | Responsibility | Why it is used |
| :--- | :--- | :--- | :--- | :--- |
| `api` | Django 5.2 + DRF | `8080` | REST API, Django admin, static assets | Core application runtime and single API surface for the SPA. |
| `worker` | Django RQ | — | Background/async jobs off the request path | Keeps long-running work (e.g. generation, e-mail) out of the request cycle. |
| `postgres` | `postgres:16` | `5432` | Primary datastore for the app **and** Keycloak | A single managed relational store; a dedicated `keycloak` DB is created by `init-keycloak-db.sh` to isolate IDP data. |
| `redis` | `redis:6` | — | Cache and RQ broker | Fast cache plus the queue backend the worker consumes. |
| `minio` | MinIO (S3-compatible) | `9000`/`9001` | Object storage for media uploads | Local, S3-compatible storage so file handling matches production S3 without an AWS dependency. |
| `keycloak` | `quay.io/keycloak/keycloak:22.0.1` | `8081` | Identity Provider (OIDC) | Externalizes authentication so the app never stores credentials itself (see Authentication below). |
| `maildev` | `maildev/maildev` | `1080` | Local SMTP + web mail inbox | Lets developers exercise transactional e-mail flows without sending real mail. |

### Authentication: Keycloak & OIDC
Authentication is delegated to **Keycloak** over **OpenID Connect (OIDC)**;
the application never manages passwords directly.

* **Container:** The `keycloak` service runs `start-dev` on `:8081` with a
  Postgres backend (`KC_DB=postgres`, database `keycloak`). The default
  bootstrap admin is `admin` / `admin` for local development only.
* **Pluggable provider:** `survey_designer/settings.py` selects the auth
  backend from the `IDENTITY_PROVIDER` environment variable. The default is
  `core.auth.backends.OIDCAuthenticationBackend` (Keycloak); setting
  `IDENTITY_PROVIDER=CIAM` switches to
  `core.auth.backends.OIDCAuthenticationBackendCIAM`.
* **Configuration:** The OIDC integration is driven entirely by environment
  variables (see `dj-be/.env.sample`):
  `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_ENDPOINT` (token introspection),
  `OIDC_AUTHORIZATION_ENDPOINT`, `OIDC_TOKEN_ENDPOINT`, `OIDC_JWKS_ENDPOINT`,
  `OIDC_CONFIGURATION_ENDPOINT`, `OIDC_USERINFO_ENDPOINT`, and
  `OIDC_CALLBACK_URL`. These point at a realm such as
  `https://keycloak.domain.org/realms/survey-designer/...`.
* **Why Keycloak / OIDC is used:** It provides standards-based SSO, keeps
  credential handling out of the application, and — through the pluggable
  backend — lets the same codebase authenticate against either a
  self-hosted Keycloak realm or WFP's CIAM without code changes.

### Localization Pipeline (i18next + `translationcli.py`)
Multi-language support is handled **on the frontend** and the translation files
live in the repository — there is no runtime translation service.

* **Runtime:** The SPA uses **i18next** (`react-ui/src/locales/i18n.ts`) with
  `i18next-http-backend` and `i18next-browser-languagedetector`. English is the
  `fallbackLng`. Supported locales: `en`, `es`, `fr`, `ar`, `pt`, `ru`, each
  with its own `translations.json`.
* **Source of truth:** `en/translations.json` is authored by hand. Every other
  locale is generated from it.
* **Generation:** `pnpm translate` (see `react-ui/package.json`) installs
  `deep_translator` + `tabulate` and runs `dj-be/translationcli.py`, which loads
  the English JSON and, using `deep_translator`'s `GoogleTranslator`,
  recursively translates every string into each language in
  `CURRENT_SUPPORTED_LANGUAGES`, writing one `translations.json` per locale.
  The script then runs `pnpm run build`.
* **Why this approach is used:** Keeping locale JSON in-repo means translations
  are versioned, reviewable in pull requests, and shipped as static assets with
  the build — no external translation platform or network dependency at
  runtime. Machine translation via `translationcli.py` gives contributors a
  fast, zero-cost baseline for all supported languages from a single
  hand-maintained English source, which can then be refined by hand where
  needed.

---

## 🔄 2. Trunk-Based Development (TBD)

We strictly practice **Trunk-Based Development** to keep our release cycles fast, minimize merge conflicts, and enforce high integration frequency.

```
                  (trunk) main
-----------------------*-----------------*----------------------->
                        \               /
                         \--[Feature]--/
                         (Short-lived branch)
```

### Core Commitments of TBD:
1. **Ticket / Issue Requirement:** For every change request (CR) or issue, a ticket must be created in the issue tracker before any code is written.
2. **Standardized Branch Naming:** Every code change must be developed in a branch named using the format `<issue-number>-<short-description>` (e.g., `42-fix-login-error` or `105-add-survey-wizard`).
3. **Target Destination:** All feature and bug fix branches must target the `main` branch as their destination.
4. **PR Review & Approval:** Once work is complete, a Pull Request (PR) must be opened targeting the `main` branch. The PR must be reviewed and approved by at least one maintainer or collaborator before it can be merged.
5. **Short-Lived Branches:** Feature and bug fix branches must be short-lived (ideally merged within 1–2 days). Avoid long-running feature branches that diverge from the `main` trunk.
6. **Atomic Changes:** Keep pull requests focused on a single logical change. If a task is complex, break it down into smaller, sequential PRs using feature flags if necessary.
7. **Frequent Merges:** Pull the latest changes from `main` into your branch daily to resolve conflicts early.
8. **Tagging & CI/CD Release:** Every stable production release from `main` must be tagged using our standardized SemVer tagging strategy (starting at `v2.0.0`) in accordance with the [Release Management & Tagging Strategy](RELEASE_MANAGEMENT.md). Pushing these tags triggers the automated build pipelines.

---

## 💻 3. Environment & Development Workflows

To support developers across different operating systems and workflows, we provide a hybrid setup: a **containerized backend** for consistency, and a **local frontend** for maximum performance and hot-reloading speed.

### ⚙️ Backend: Containerized Django Environment
The backend requires complex service coordination (database, cache, identity provider, object storage, etc.). To eliminate "works on my machine" issues, the entire backend runs inside isolated Docker containers.

> [!TIP]
> The backend container leverages **Python 3.11** managed via **Poetry** to guarantee deterministic dependency resolution.

* **Development Command:** Run `docker compose up --build` from the `dj-be` directory to orchestrate all services including Keycloak, Postgres, Redis, MinIO, and Maildev.
* **Service Isolation:** Port boundaries and environment variables are strictly mapped via `.env` configurations.

### 🎨 Frontend: Local ReactJS & Vite Environment
The frontend is built with **ReactJS** and **TypeScript** using **Vite** as a lightning-fast build tool and dev server. It is executed locally directly on your host machine.

> [!IMPORTANT]
> The frontend requires **Node.js 20.x** and **pnpm** (version 10.8.0) to ensure fast dependency installs and optimal build performance.

* **Development Command:** From the `react-ui` directory, run `pnpm install` followed by `pnpm dev`.
* **Hot-Reloading:** Running the frontend locally provides instant feedback through Vite's Hot Module Replacement (HMR).
* **Decoupled Connectivity:** Configure your local frontend to point to the backend container API via the `VITE_APP_API_ENDPOINT` variable.

---

## 🛡️ 4. Core Engineering Values

### Clean Code & Standard Conventions
* **Lints and Formatting:** We enforce automated code styling. Run `pnpm run lint` and `pnpm run pretty` for the frontend. For Python, use our `pre-commit` hooks containing Black/Flake8 linters.
* **TypeScript & Static Typing:** We maintain type safety across the frontend to catch bugs at compile-time. Avoid `any` types; prefer robust interfaces and types.

### Test Automation & CI Compliance
No code should be merged without validation. Run tests locally prior to pushing your commits:

| Environment | Test Command | Technology |
| :--- | :--- | :--- |
| **Frontend** | `pnpm test:ci` | Vitest / Testing Library |
| **Backend** | `docker compose run api test-ci` | Django Unit Tests / Pytest |
| **End-to-end** | `pnpm e2e:ci` | Playwright (real Django stack) |

#### Branch Coverage Requirement

> [!IMPORTANT]
> **Branch coverage must be greater than 85%** for every change. Coverage is
> collected with *branch* coverage enabled so that both sides of each
> conditional are exercised, not just line coverage.

* **Frontend:** `pnpm test:ci` runs `vitest run --coverage` using
  `@vitest/coverage-v8`. Coverage is reported to the `coverage/` directory
  (`text` and `cobertura` reporters).
* **Backend:** `pytest` runs with `--cov survey_designer` and `branch = True`
  (see `dj-be/setup.cfg`), producing XML, HTML, and terminal reports.

> [!WARNING]
> **Current configuration does not yet enforce the 85% target automatically.**
> At present the backend gate is `--cov-fail-under 70` in `dj-be/setup.cfg`, and
> the frontend (`react-ui/vite.config.js`) sets no coverage threshold at all.
> Until these are aligned, reviewers must verify the 85% branch-coverage
> requirement manually. To enforce it automatically, raise the backend gate to
> `--cov-fail-under 85` and add a Vitest `coverage.thresholds` block (for
> example `{ branches: 85 }`). Changing these gates can cause currently passing
> pipelines to fail if existing coverage is below 85%, so coordinate the change
> with the maintainers.

* **End-to-end:** Playwright drives the frontend against the real local Django
  stack (the API is not mocked). See
  [`react-ui/e2e/README.md`](../../../react-ui/e2e/README.md) for setup,
  authentication via `POST /auth/e2e-login/`, and CI details.

### GNU AGPL-3.0 License Compliance
Survey Designer is open-source software licensed under the **GNU Affero General Public License v3**.

> [!WARNING]
> Every contributor must ensure that any new dependency, library, package, or utility introduced to either the frontend or backend is strictly compatible with the AGPL-3.0 license. Proprietary or non-permissively licensed packages are strictly forbidden.

### Security-First Defaults
* **Secure Communications:** Standardized authentication via **Keycloak (OIDC)** is integrated into the core login flow.
* **Vulnerability Scanning:** Security checks (e.g., Trivy container scans) are periodically run to identify and resolve CVEs early.
* **Vulnerability Disclosure:** In the event of a security discovery, do **not** open a public issue. Email the details directly to **global.surveydesigner@wfp.org**.

---

## 🤝 5. Empathetic Code Reviews

We view pull request reviews as collaborative mentoring sessions rather than gating processes.

* **Supportive & Pragmatic:** The primary objective is to improve the codebase, while the secondary objective is to support the contributor's growth.
* **Micro-Optimizations:** Avoid nitpicking and micro-optimizations. Focus reviews on correctness, security, architectural alignment, test coverage, and readability.
* **Clear Feedback:** Clearly label minor feedback as a `Nit:` to indicate it does not block the landing of the PR.
