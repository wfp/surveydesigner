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
    end

    subgraph Service-Side (Docker Containerized)
        Backend[Django Backend]
        DB[(PostgreSQL)]
        Cache[(Redis Cache)]
        Storage[(MinIO Storage)]
        Auth[Keycloak IDP]
        Mail[Maildev SMTP]
    end

    React <-->|REST APIs / JSON| Backend
    Backend <--> DB
    Backend <--> Cache
    Backend <--> Storage
    Backend <--> Auth
```

### Decoupled Architecture
* **Strict Separation of Concerns:** The frontend (**ReactJS**) and backend (**Django**) are fully decoupled. They communicate exclusively via standardized, versioned RESTful APIs.
* **Independent Runtimes:** The frontend runs as a Single Page Application (SPA) in the user's browser, while the backend is an API provider and task executor running inside containerized services.

### Monorepo Approach
* **Single Source of Truth:** Both the frontend (`react-ui`) and backend (`dj-be`) reside in a single repository. This enables atomic commits across layers, facilitates co-dependent changes, and simplifies repository discovery.
* **Unified Tooling & Guidelines:** All documentation, licensing, security protocols, and shared developer environments are consolidated, simplifying onboarding and ensuring compliance.

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

### GNU AGPL-3.0 License Compliance
Survey Designer is open-source software licensed under the **GNU Affero General Public License v3**.

> [!WARNING]
> Every contributor must ensure that any new dependency, library, package, or utility introduced to either the frontend or backend is strictly compatible with the AGPL-3.0 license. Proprietary or non-permissively licensed packages are strictly forbidden.

### Security-First Defaults
* **Secure Communications:** Standardized authentication via **Keycloak (OIDC)** is integrated into the core login flow.
* **Vulnerability Scanning:** Security checks (e.g., Trivy container scans) are periodically run to identify and resolve CVEs early.
* **Vulnerability Disclosure:** In the event of a security discovery, do **not** open a public issue. Email the details directly to **leandro.bravo@wfp.org**.

---

## 🤝 5. Empathetic Code Reviews

We view pull request reviews as collaborative mentoring sessions rather than gating processes.

* **Supportive & Pragmatic:** The primary objective is to improve the codebase, while the secondary objective is to support the contributor's growth.
* **Micro-Optimizations:** Avoid nitpicking and micro-optimizations. Focus reviews on correctness, security, architectural alignment, test coverage, and readability.
* **Clear Feedback:** Clearly label minor feedback as a `Nit:` to indicate it does not block the landing of the PR.
