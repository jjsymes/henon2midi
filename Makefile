.ONESHELL:
ENV_PREFIX := $(shell python3 -c "if __import__('pathlib').Path('.venv/bin/pip').exists(): print('.venv/bin/')")
EXTRA_ARGS?=
PYTHON_COMMAND?=python3

.PHONY: help
help: ## Show the help.
	@echo "Usage: make [target] [EXTRA_ARGS=...]"
	@echo ""
	@echo "Targets:"
	@fgrep "##" Makefile | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

.PHONY: show
show: ## Show the environment.
	@echo "Current environment:"
	@echo "Running using $(ENV_PREFIX)"
	@$(ENV_PREFIX)python --version
	@$(ENV_PREFIX)python -m henon2midi --version

.PHONY: install
install: activate ## Install the in dev mode
	@echo "Don't forget to run 'make virtualenv' if you get errors"
	$(ENV_PREFIX)pip install -e .[test]

.PHONY: fmt
fmt: activate ## Format code using black and isort
	$(ENV_PREFIX)isort henon2midi/
	$(ENV_PREFIX)black henon2midi/
	$(ENV_PREFIX)black tests/

.PHONY: lint
lint: activate ## Run pep8, black, mypy linters
	$(ENV_PREFIX)flake8 henon2midi/
	$(ENV_PREFIX)black --check henon2midi/
	$(ENV_PREFIX)black --check tests/
	$(ENV_PREFIX)mypy --ignore-missing-imports henon2midi/

.PHONY: test
test: activate ## Run tests
	$(ENV_PREFIX)pytest -v -l --tb=short --maxfail=1 tests/
	$(ENV_PREFIX)coverage xml
	$(ENV_PREFIX)coverage html

.PHONY: watch
watch: ## Run tests on every change
	ls **/**.py | entr $(ENV_PREFIX)pytest -s -vvv -l --tb=long --maxfail=1 tests/

.PHONY: clean
clean: ## Clean unused files
	@find ./ -name "*.pyc" -exec rm -rf {} \;
	@find ./ -name "__pycache__" -exec rm -rf {} \;
	@find ./ -name "Thumbs.db" -exec rm -rf {} \;
	@find ./ -name "*~" -exec rm -rf {} \;
	@rm -rf .cache
	@rm -rf .pytest_cache
	@rm -rf .mypy_cache
	@rm -rf build
	@rm -rf dist
	@rm -rf *.egg-info
	@rm -rf htmlcov

.PHONY: virtualenv
virtualenv: ## Create a virtual environment
	@echo "Creating virtualenv..."
	@rm -rf .venv
	@$(PYTHON_COMMAND) -m venv .venv
	@./.venv/bin/pip install -U pip
	@./.venv/bin/pip install -e .[test]
	@echo ""
	@echo "!!! Please run 'source .venv/bin/activate' to activate the virtualenv !!!"

.PHONY: activate
activate: ## Activate the virtual environment
	@echo "Activating virtualenv..."
	. ./$(ENV_PREFIX)activate

HENON := $(ENV_PREFIX)python -m henon2midi

.PHONY: run
run: ## Run the historical defaults. About 100 orbits; it also plays MIDI. EXTRA_ARGS="..." adds flags.
	$(HENON) $(EXTRA_ARGS)

.PHONY: example-classic
example-classic: ## Draw a short classic orbit. No MIDI device needed.
	$(HENON) --visualize-only -i 8 -s 0.1 $(EXTRA_ARGS)

.PHONY: example-sweep
example-sweep: ## Classic map. Each orbit starts one radian further around the circle.
	$(HENON) --visualize-only --start sweep -i 6 -s 0.1 $(EXTRA_ARGS)

.PHONY: example-four
example-four: ## Four-parameter map, coefficients 2 2 2 2, swept start. Draws only.
	$(HENON) --visualize-only --map four-parameter -p 2,2,2,2 --start sweep -i 8 -s 0.1 $(EXTRA_ARGS)

.PHONY: example-rotation
example-rotation: ## Custom rotation, x'=y and y'=-x. No -p. Draws only.
	$(HENON) --visualize-only --x-prime=y --y-prime=-x --start sweep -i 8 -s 0.2 $(EXTRA_ARGS)

.PHONY: example-file
example-file: ## Write sweep.mid and play it. Needs a MIDI output. make list-midi shows the names.
	$(HENON) --out sweep.mid --start sweep -i 8 -s 0.2 $(EXTRA_ARGS)

.PHONY: list-midi
list-midi: ## Print MIDI output names and exit.
	$(HENON) --list-midi-outputs

.PHONY: build
build: ## Build the project
	$(ENV_PREFIX)python -m build

.PHONY: tag
tag: ## Create a new tag for a release
	@echo "WARNING: This operation will create a new tag and push it to the remote repository."
	@read -p "Version? (e.g. 0.1.0): " TAG && \
	sed -i "" "s/version = \"[0-9]\.[0-9]\.[0-9]\"/version = \"$${TAG}\"/g" pyproject.toml && \
	git add pyproject.toml && \
	git commit -m "release: version $${TAG}" && \
	echo "creating git tag : $${TAG}" && \
	git tag $${TAG} && \
	git push -u origin HEAD --tags

.PHONY: release
release: build ## push the package to pypi
	$(ENV_PREFIX)python -m twine upload dist/*

.PHONY: pre-commit-install
pre-commit-install: activate ## Install pre-commit hooks
	pre-commit install

.PHONY: pre-commit-uninstall
pre-commit-uninstall: activate ## Uninstall pre-commit hooks
	pre-commit uninstall

.PHONY: pre-commit-run
pre-commit-run: activate ## Run pre-commit hooks
	pre-commit run --all-files

.PHONY: variables
variables: ## Show interesting variables
	@echo "ENV_PREFIX: $(ENV_PREFIX)"
	@echo "EXTRA_ARGS: $(EXTRA_ARGS)"
