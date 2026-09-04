PYTHON=python3
PIP=pip3
PROJECT_NAME=survey_designer

start: collectstatic migrate run

lint:
	flake8 --exclude migrations $(PROJECT_NAME)
	black --check --diff --exclude migrations $(PROJECT_NAME)
	isort --check-only $(PROJECT_NAME)

fmt:
	autoflake -ri --remove-all-unused-imports --remove-unused-variables --expand-star-imports --remove-duplicate-keys $(PROJECT_NAME)
	isort $(PROJECT_NAME)
	black --exclude migrations $(PROJECT_NAME)

clean:
	rm -f test-results.xml
	rm -rf .tox
	find . -name "*.pyc" | xargs rm -f
	find . -name "__pycache__" | xargs rm -rf

install-req:
	pip install -r /tmp/dev-requirements.txt

test: lint
	$(PYTHON) manage.py makemigrations --check
	pytest

test-ci: install-req test

migrate:
	$(PYTHON) manage.py migrate --noinput
	$(PYTHON) manage.py init_users
	$(PYTHON) manage.py generate_data
# E2E-only seed relations; enabled by the E2E compose environment.
ifeq ($(E2E_INIT_DATA),true)
	$(PYTHON) manage.py init_e2e_data
endif
	$(PYTHON) manage.py fix_module_ordering
	$(PYTHON) manage.py init_frontend_content
	$(PYTHON) manage.py update_group_permissions
	$(PYTHON) manage.py normalise_ordering

makemigrations:
	$(PYTHON) manage.py makemigrations

mergemigrations:
	$(PYTHON) manage.py makemigrations --merge

collectstatic:
	$(PYTHON) manage.py collectstatic --noinput

set-build_id:
	echo '___version___ = "${BUILD_ID}"' > ./$(PROJECT_NAME)/__init__.py

healthcheck:
	$(PYTHON) manage.py health_check

worker:
	$(PYTHON) manage.py rqworker --pid /tmp/generic-worker.pid generic & \
	$(PYTHON) manage.py rqworker --pid /tmp/generate-doc-worker.pid generate-doc & \
	$(PYTHON) manage.py rqworker --pid /tmp/email-worker.pid send-email

run_dev:
	$(PYTHON) manage.py runserver 0:8080

run:
	gunicorn $(PROJECT_NAME).asgi:application -w 4 -b :8080 -k uvicorn.workers.UvicornWorker \
	--capture-output \
	--enable-stdio-inheritance \
	--log-level=debug \
	--access-logfile=- \
	--log-file=- \
	--threads=2 \
	--timeout=300 \
	--keep-alive=60 \
	--pid=/tmp/gunicorn.pid \
	--reload

shell:
	$(PYTHON) manage.py shell

shell_plus:
	$(PYTHON) manage.py shell_plus
