# Survey Designer Documentation

Welcome! This directory contains the contributor, governance, and process
documentation for the **Survey Designer** project — an application for building
XLSForm/ODK-based surveys while maintaining WFP standard labeling and naming
conventions.

Survey Designer is a **decoupled monorepo**:

* `react-ui/` — React 18 + TypeScript frontend built with Vite, tested with
  Vitest and Playwright.
* `dj-be/` — Django 5.2 backend (REST API + Django admin) with PostgreSQL,
  Redis, MinIO, and Keycloak, tested with pytest.

For product setup and how to run the application, see the
[repository README](../README.md).

## Getting started as a contributor

| Document | What it covers |
| :--- | :--- |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution workflow, branch naming, testing and security requirements, license compliance. |
| [BUILDING.md](BUILDING.md) | How to build the frontend artifact and the backend Docker image. |
| [ONBOARDING.md](ONBOARDING.md) | Local setup for both apps, running tests and Playwright e2e, and what new collaborators are expected to know. |
| [Technical Values & Development Principles](doc/contributing/TECHNICAL_VALUES.md) | Architecture, trunk-based development, environments, engineering values, testing, and coverage requirements. |
| [Release Management & Tagging Strategy](doc/contributing/RELEASE_MANAGEMENT.md) | Semantic Versioning, Git tagging rules, release paths, and the release workflow. |

## Governance and community

| Document | What it covers |
| :--- | :--- |
| [GOVERNANCE.md](GOVERNANCE.md) | Roles (triagers, collaborators, the maintainers team), nominations, decision-making, and the consensus-seeking process. |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Expected behavior and enforcement guidelines. |
| [MODERATION_POLICY.md](MODERATION_POLICY.md) | How moderation requests are made and handled. |
| [Working Groups](WORKING_GROUPS.md) | How focused working groups are chartered and operate. |
| [Roadmap Guidance](doc/ROADMAP_GUIDANCE.md) | How the roadmap is tracked and how to propose items. |

## Testing and quality at a glance

Every change must pass the checks below before it can be merged. Full details
are in [CONTRIBUTING.md](CONTRIBUTING.md) and
[Technical Values](doc/contributing/TECHNICAL_VALUES.md).

| Area | Command | Tooling |
| :--- | :--- | :--- |
| Frontend unit tests + coverage | `pnpm test:ci` | Vitest + `@vitest/coverage-v8` |
| Frontend lint / format / types | `pnpm lint`, `pnpm pretty`, `pnpm tsc` | ESLint, Prettier, TypeScript |
| Backend tests + coverage | `docker compose run api test-ci` (or `make test`) | pytest + pytest-cov |
| End-to-end | `pnpm e2e:ci` | Playwright (see [`react-ui/e2e/README.md`](../react-ui/e2e/README.md)) |

> [!IMPORTANT]
> **Branch coverage must be greater than 85%.** Coverage is measured with
> branch coverage enabled (`branch = True` for the backend, `@vitest/coverage-v8`
> for the frontend). See
> [Technical Values → Test Automation & CI Compliance](doc/contributing/TECHNICAL_VALUES.md#test-automation--ci-compliance)
> for details and the current configuration status.

## Reporting security issues

Do **not** open a public issue for security vulnerabilities. Email
**global.surveydesigner@wfp.org** — see the Security Protocol in
[CONTRIBUTING.md](CONTRIBUTING.md#-security-protocol).
