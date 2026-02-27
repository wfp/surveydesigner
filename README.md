# Survey Designer

Survey Designer is an application that allows users in the field to build
surveys in a fast and easy way while giving them the flexibility to make
necessary adjustments while also maintaining WFP standard labeling & naming
conventions.
This is to improve the overall data quality when it comes to survey design,
data collection & analysis (saving time and resources) as well as allowing for
reproducibility and sharing resources between users. This tool is targeted for
users that are using XLSForm or ODK-based tools (such as: MoDa or Kobo).

## Frontend Architecture

The application's frontend is designed as a decoupled solution from the backend.

- **Authentication**: The login process is managed securely via Keycloak.
- **Localization**: Multi-language support is handled locally, based on translation files located directly within the frontend part of the repository.

## Requirements

- PostgreSQL - Main datastore
- Redis - Caching
- Python 3.11
- poetry - python package manager
- Docker

## Setup

Some environment variables are required in order to run the application. Use
`.env.sample` as template to create an `.env` file (it will be used by the
django settings thanks to `python-dotenv`).

Example when running in a local environemnt:

```
# Django
DJANGO_SETTINGS_MODULE="wfp.settings"
SECRET_KEY='django-insecure-=!&_i6qv%8pd!l7-+d=2&-s(bu=h5pc*!^&3)c^4wc)iz8d7*3'
DEBUG=True
ALLOWED_HOSTS='domain.org;localhost;127.0.0.1'
CORS_ALLOWED_ORIGINS='http://domain.org;http://localhost:3000'
# ENV types: local, ci, dev, qa, prod
ENV=local

# Database
POSTGRES_USER=postgres
POSTGRES_DB=app_db
POSTGRES_HOST=postgres
POSTGRES_PASSWORD=r00t
POSTGRES_PORT=5432

# Redis cache
REDIS_URL=redis://redis:6379/0

# Sentry
SEND_TO_SENTRY=false
SENTRY_DSN=""
SENTRY_SAMPLE_RATE=0.001

# Upload to S3
UPLOAD_TO_S3=False

#email
EMAIL_HOST=""
EMAIL_HOST_USER=""
EMAIL_HOST_PASSWORD=""

#auth
OIDC_CLIENT_ID=""
OIDC_CLIENT_SECRET=""

```

## Run app locally

1. Configure Postgres and redis then update the .env file to point to the correct servers.
2. Run `pnpm install` to install node packages.
3. Run `pnpm dev` to start frontend dev server.
4. Run `pnpm build` to build packages for production.
5. Run `poetry install` to create a virtualenv and install all requirements.
6. Run `poetry run make` to start the application. Or you can use the django
   runserver if you prefer, just remember to run `make migrate` first.
7. Run `poetry run make test` to run tests.
8. Run `pre-commit install` to install pre-commit hooks.

## Run app inside a docker container

1. Run `docker compose up --build`. This will build and start the server.
2. If `DEBUG` is `True` then run `pnpm dev`. This will build and start the frontend.
3. Navigate to `http://localhost:8080` to view the site.

## Developing translations

With the container running

1. Add the translation key and text inside: `survey_designer/apps/frontend/src/public/locales/en/translations.json`
2. run `pnpm run translate` - This translates the files into all supported languages and creates a production build.
3. Start the Docker container. `docker compose up -d`
4. run `docker exec -it surveydesigner-api-1 make collectstatic` - Enter the containers shell
5. inside the container run `python manage.py collectstatic` - This collects all the static files (dist folder we just created) and stores them in the root static folder.
6. Start the Vite Frontend `pnpm run dev`
