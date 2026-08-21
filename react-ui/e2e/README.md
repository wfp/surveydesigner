# Playwright E2E Tests

This suite runs the React frontend against the real local Django stack. It does not mock the API.

## Local setup

Start the backend stack from the repository root:

```sh
cd dj-be
docker compose --env-file .env.e2e up -d --build
curl --fail http://localhost:8080/health/
```

Install frontend dependencies and the Chromium browser:

```sh
cd react-ui
pnpm install
pnpm exec playwright install chromium
```

Run the headless smoke suite:

```sh
pnpm e2e:ci
```

Debug interactively:

```sh
pnpm e2e:ui
```

The Playwright config starts Vite on `http://localhost:3000` and points the app at `http://localhost:8080` by default. Override with `E2E_BASE_URL` and `E2E_API_URL` if needed. For example, if port 3000 is already in use locally, run `E2E_BASE_URL=http://localhost:3002 pnpm e2e:ci`; `dj-be/.env.e2e` already allows both 3000 and 3002 for CORS.

## Authentication

Authenticated tests use `POST /auth/e2e-login/` to create a real Django session cookie for an existing seeded user. The endpoint is only registered when all conditions are true:

- `ENABLE_E2E_AUTH=true`
- `ENV` is `ci` or `test`
- `E2E_AUTH_TOKEN` is non-empty

The Playwright request must send the same token in the `X-E2E-Auth-Token` header. The committed value is only for local E2E runs; CI should use a generated or secret pipeline value:

```sh
E2E_AUTH_TOKEN=change-me-for-e2e
```

Default E2E identity is the seeded admin user from `init_users`:

```sh
E2E_USER_EMAIL=admin@wfp.org
```

## CI

`azure-pipelines.e2e.yml` is an example Azure DevOps PR pipeline. It installs pnpm and Chromium, starts `dj-be/docker-compose.yml` with `dj-be/.env.e2e`, waits for `http://localhost:8080/health/`, runs `pnpm e2e:ci`, publishes JUnit results, and uploads the Playwright HTML report plus traces/screenshots/videos from `react-ui/test-results`.

## Verification commands

```sh
cd react-ui
pnpm install
pnpm test:ci
pnpm e2e:ci
```

Backend startup is verified with:

```sh
cd dj-be
docker compose --env-file .env.e2e up -d --build
curl --fail http://localhost:8080/health/
```
