# Onboarding

This document is an outline of the things we tell new collaborators at their
onboarding session.

> [!NOTE]
> **Open access & public contributions:** The Survey Designer repository is a
> fully public repository. Anyone who requests access and is approved by the
> SurveyDesigner maintainers team can contribute. We
> actively encourage public participation and aim to maintain a welcoming,
> low-barrier entry point for all qualified collaborators.

## Contents

* [Before the onboarding session](#before-the-onboarding-session)
* [Onboarding session](#onboarding-session)
* [Repository layout](#repository-layout)
* [Local setup](#local-setup)
  * [Backend (Django, containerized)](#backend-django-containerized)
  * [Frontend (React, local)](#frontend-react-local)
  * [End-to-end tests (Playwright)](#end-to-end-tests-playwright)
* [Project goals and values](#project-goals-and-values)
* [Managing the issue tracker](#managing-the-issue-tracker)
* [Reviewing pull requests](#reviewing-pull-requests)
* [Landing pull requests](#landing-pull-requests)
* [Final notes](#final-notes)

## Before the onboarding session

* If the new collaborator is not yet a member of the WFP GitHub organization,
  confirm that they are using [two-factor authentication][]. It will not be
  possible to add them to the organization if they are not using two-factor
  authentication.
* Prior to the onboarding session, add the new collaborator to the
  [@wfp/surveydesigner team][the collaborators team].
* Confirm the new collaborator has Docker, Node.js 20.x, `pnpm`, Python 3.11,
  and Poetry available locally (see [Local setup](#local-setup)).

## Onboarding session

This session will cover:

* [local setup](#local-setup)
* [project goals and values](#project-goals-and-values)
* [managing the issue tracker](#managing-the-issue-tracker)
* [reviewing pull requests](#reviewing-pull-requests)
* [landing pull requests](#landing-pull-requests)

## Repository layout

Survey Designer is a **decoupled monorepo**. The two applications live in the
same repository but run as independent runtimes:

| Directory | Application | Stack |
| :--- | :--- | :--- |
| `react-ui/` | Frontend Single Page Application | React 18, TypeScript, Vite, Vitest, Playwright |
| `dj-be/` | Backend API and Django admin | Django 5.2, Django REST Framework, PostgreSQL, Redis, MinIO, Keycloak |
| `docs/` | Project and governance documentation | Markdown |
| `.github/` | Issue templates and GitHub workflows | — |

For a deeper explanation of the architecture and engineering principles, read
the [Technical Values and Development Principles][Technical Values] document.

## Local setup

* git:
  * Always create a branch in your own GitHub fork for pull requests.
    Branches in the `surveydesigner` repository are reserved for release lines.
  * Add the canonical `surveydesigner` repository as the `upstream` remote:
    * `git remote add upstream git@github.com:wfp/surveydesigner.git`
  * To update from `upstream`:
    * `git checkout main`
    * `git fetch upstream HEAD`
    * `git reset --hard FETCH_HEAD`
  * Make a new branch for each pull request you submit, following the branch
    naming standard in [CONTRIBUTING.md][] (for example
    `issue/42-fix-login`).
  * Membership: consider making your membership in the WFP GitHub organization
    public. This makes it easier to identify collaborators. See
    [Publicizing or hiding organization membership][].

* Install `pre-commit` hooks in each application you work on:
  * `pre-commit install` (a `.pre-commit-config.yaml` exists in both
    `react-ui/` and `dj-be/`).

### Backend (Django, containerized)

The backend requires coordinated services (PostgreSQL, Redis, MinIO, Keycloak,
Maildev). To avoid "works on my machine" issues, it runs entirely in Docker.

```sh
cd dj-be
cp .env.sample .env          # then adjust values as needed
docker compose up --build    # starts api, worker, postgres, redis, minio, keycloak, maildev
```

* The API is served on `http://localhost:8080` (Keycloak on `:8081`, Maildev on
  `:1080`, MinIO console on `:9001`).
* Django management tasks are wrapped in the `dj-be/Makefile`. Common targets:
  * `make migrate` — run migrations and seed data (`init_users`,
    `generate_data`, etc.).
  * `make run_dev` — Django `runserver` on `0:8080`.
  * `make lint` — `flake8`, `black --check`, `isort --check-only`.
  * `make test` — lint, `makemigrations --check`, then `pytest`.
  * `make collectstatic` — collect static assets.

### Frontend (React, local)

The frontend runs locally on the host for fast Hot Module Replacement.

```sh
cd react-ui
pnpm install
pnpm dev            # Vite dev server on http://localhost:3000
```

Point the frontend at the backend container through the
`VITE_APP_API_ENDPOINT` environment variable. Useful scripts (from
`react-ui/package.json`):

* `pnpm dev` — Vite dev server.
* `pnpm build` — production build to `dist/`.
* `pnpm lint` / `pnpm lint:fix` — ESLint over `src/app`.
* `pnpm pretty` — Prettier formatting.
* `pnpm tsc` — TypeScript type check (`tsc --noEmit`).
* `pnpm test` — Vitest in watch mode.
* `pnpm test:ci` — `vitest run --coverage` (used for CI and pre-merge checks).

### End-to-end tests (Playwright)

Playwright drives the React frontend against the **real** local Django stack —
the API is not mocked. Full details are in [`react-ui/e2e/README.md`][e2e readme].

```sh
# 1. Start the backend stack with the E2E environment file
cd dj-be
docker compose --env-file .env.e2e up -d --build
curl --fail http://localhost:8080/health/

# 2. Install the browser and run the headless smoke suite
cd ../react-ui
pnpm install
pnpm exec playwright install chromium
pnpm e2e:ci        # playwright test --project=chromium
```

Interactive debugging is available with `pnpm e2e:ui`. Authenticated tests use
`POST /auth/e2e-login/`, which is only registered when `ENABLE_E2E_AUTH=true`,
`ENV` is `ci` or `test`, and `E2E_AUTH_TOKEN` is set (see the e2e README).

## Project goals and values

* Collaborators are the collective owners of the project.
  * The project has the goals of its contributors.

* There are some higher-level goals and values:
  * Empathy towards users matters (this is in part why we onboard people).
  * Generally: try to be nice to people!
  * The best outcome is for people who come to our issue tracker to feel like
    they can come back again.
  * Understand our decoupled architecture, the local `pnpm`/Vite frontend
    environment, the dockerized Django backend, and our trunk-based development
    workflow by reviewing the [Technical Values and Development Principles][Technical Values].

* You are expected to follow _and_ hold others accountable to the
  [Code of Conduct][].

## Managing the issue tracker

* You have (mostly) free rein; don't hesitate to close an issue if you are
  confident that it should be closed.
  * Be nice about closing issues! Let people know why, and that issues and pull
    requests can be reopened if necessary.

* Issues are created from the templates in [`.github/ISSUE_TEMPLATE`][issue templates]
  (Bug, Feature, Epic, User Story, Task).
  * The [Issue Hierarchy Validator][] GitHub workflow enforces parent/child
    relationships between Epics, Features, User Stories, and Tasks. If an issue
    is missing a valid parent, the workflow comments and applies the
    `invalid-hierarchy` label.
  * Feel free to apply relevant labels and remove irrelevant labels from pull
    requests and issues.
  * When a change has the remote _chance_ of breaking something, treat it as a
    `MAJOR` change per our [Release Management & Tagging Strategy][Release Management].

* When a discussion gets heated, you can request that other collaborators keep
  an eye on it. Refer to the [Moderation Policy][] for the full process and the
  [list of Moderation Team members][moderation members].

## Reviewing pull requests

* The primary goal is for the codebase to improve.

* Secondary (but not far off) is for the person submitting code to succeed. A
  pull request from a new contributor is an opportunity to grow the community.

* Review a bit at a time. Do not overwhelm new contributors.

* Be aware: your opinion carries a lot of weight!

* Nits (requests for small changes that are not essential) are fine, but try to
  avoid stalling the pull request.
  * Identify them as nits when you comment: `Nit: change foo() to bar().`
  * If they are stalling the pull request, fix them yourself on merge.

* Insofar as possible, issues should be identified by tools (ESLint, Prettier,
  `tsc`, flake8, black, isort) rather than human reviewers.

* Verify the required checks before approving:
  * Frontend: `pnpm lint`, `pnpm tsc`, and `pnpm test:ci` pass.
  * Backend: `make test` (or `docker compose run api test-ci`) passes.
  * Branch coverage must be **greater than 85%** (see
    [CONTRIBUTING.md][] and [Technical Values][]).
  * Where relevant, the Playwright suite (`pnpm e2e:ci`) passes.
  * A Trivy scan reports no new vulnerabilities.

* Minimum wait for comments time:
  * For non-trivial changes, leave the pull request open for at least 48 hours
    so people in a distributed project can respond.
  * If a pull request is abandoned, check if the author would mind if you took
    it over (especially if it just has nits left).

* Approving a change:
  * Collaborators approve using GitHub's review interface.
  * You have the authority to approve any other collaborator's work.
  * You cannot approve your own pull requests.
  * Two collaborator approvals are required before a pull request can land (one
    is enough if the pull request has been open for more than 7 days). See
    [GOVERNANCE.md][the collaborators team].

## Landing pull requests

* We use a **monorepo** with **trunk-based development**. All feature and bug
  fix branches target `main` and should be short-lived.
* Commits in one pull request that belong to one logical change should be
  squashed before landing.
* Ensure the pull request description links the relevant GitHub issue.
* For our versioning conventions, tagging strategy, and semantic versioning
  rules, refer to the [Release Management & Tagging Strategy][Release Management].

## Final notes

* Don't worry about making mistakes: everybody makes them, there's a lot to
  internalize and that takes time (and we recognize that!).
* Almost any mistake you could make can be fixed or reverted.
* The existing collaborators trust you and are grateful for your help!
* The project has a venue for real-time discussion on the
  [WFP Slack Community][], and asynchronous discussion in
  [GitHub Discussions][].

[CONTRIBUTING.md]: CONTRIBUTING.md
[Code of Conduct]: CODE_OF_CONDUCT.md
[GitHub Discussions]: https://github.com/wfp/surveydesigner/discussions
[Issue Hierarchy Validator]: ../.github/workflows/issue-hierarchy-validator.yml
[Moderation Policy]: MODERATION_POLICY.md
[Publicizing or hiding organization membership]: https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-personal-account-on-github/managing-your-membership-in-organizations/publicizing-or-hiding-organization-membership
[Release Management]: doc/contributing/RELEASE_MANAGEMENT.md
[Technical Values]: doc/contributing/TECHNICAL_VALUES.md
[WFP Slack Community]: https://wfp.slack.com/
[e2e readme]: ../react-ui/e2e/README.md
[issue templates]: ../.github/ISSUE_TEMPLATE
[moderation members]: MODERATION_POLICY.md#current-members-of-moderation-team
[the collaborators team]: GOVERNANCE.md#collaborators
[two-factor authentication]: https://docs.github.com/en/authentication/securing-your-account-with-two-factor-authentication-2fa/configuring-two-factor-authentication
