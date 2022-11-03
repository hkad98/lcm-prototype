.PHONY: dev
dev:
	python3.10 -m venv .venv --upgrade-deps
	.venv/bin/pip3 install -r requirements.txt
	.venv/bin/pre-commit install

.PHONY: fix
fix:
	make format-fix
	make lint


.PHONY: format-fix
format-fix:
	black .
	isort .

.PHONY: lint
lint:
	flake8 .
