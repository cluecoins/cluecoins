.PHONY: $(MAKECMDGOALS)
MAKEFLAGS += --no-print-directory
##
##  🚧 Cluecoins developer tools
##
PACKAGE=cluecoins
TAG=latest
SOURCE=src tests


help:           ## Show this help (default)
	@grep -Fh "##" $(MAKEFILE_LIST) | grep -Fv grep -F | sed -e 's/\\$$//' | sed -e 's/##//'

install:        ## Install dependencies
	uv sync --all-extras --all-groups --link-mode symlink --locked

update:         ## Update dependencies and dump requirements.txt
	uv sync -U --all-extras --all-groups --link-mode symlink

all:            ## Run an entire CI pipeline
	make format lint test

format:         ## Format with all tools
	ruff format ${SOURCE}

lint:           ## Lint with all tools
	ruff check --fix --unsafe-fixes ${SOURCE}
	mypy ${SOURCE}

test:           ## Run tests
	COVERAGE_CORE=sysmon pytest tests

##
