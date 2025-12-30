FROM python:3.11-slim as python-base
ENV PYTHONUNBUFFERED=true \
  VENV_PATH=/opt/venv
ENV PATH="$VENV_PATH/bin:$PATH"

ARG BUILD_ID

WORKDIR /app

# Update all packages (security)
RUN apt-get update && apt-get dist-upgrade -y && apt-get autoremove -y && apt-get autoclean -y

FROM python-base as builder
ENV POETRY_HOME=/opt/poetry
ENV PATH="$POETRY_HOME/bin:$PATH"
ENV POETRY_VERSION=1.3.2

# Install system packages
RUN apt-get install -y --no-install-recommends \
  make gcc curl

# install poetry - uses $POETRY_VERSION and $POETRY_HOME internally
RUN curl -sSL https://install.python-poetry.org | python3 -
RUN poetry config virtualenvs.create false --local

COPY poetry.lock pyproject.toml ./
# dump requirements
RUN poetry export -f requirements.txt --without dev -o /tmp/requirements.txt
RUN poetry export -f requirements.txt --only dev -o /tmp/dev-requirements.txt


RUN python3 -m venv $VENV_PATH
RUN pip3 install -r /tmp/requirements.txt

FROM python-base as runtime
COPY --from=builder /usr/bin/make /usr/bin/make
COPY --from=builder $VENV_PATH $VENV_PATH
COPY --from=builder /tmp/dev-requirements.txt /tmp/dev-requirements.txt

COPY . ./

# Set build id
RUN make set-build_id BUILD_ID=${BUILD_ID}

HEALTHCHECK --interval=30s --retries=5 --timeout=10s  CMD [ "make", "healthcheck" ]

EXPOSE 8080

ENTRYPOINT ["make"]
