# Thin wrappers over the sdd skill scripts. Every path comes from sdd.yaml.
SDD  := python3 .claude/skills/sdd/scripts
BASE ?= demo/trunk

.DEFAULT_GOAL := help
.PHONY: help check test dial trace trace-design fresh contract mutate evidence land board board-reset

help: ## list the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  make %-13s %s\n", $$1, $$2}'

check: ## run every gate the dial requires for the specs in this repo (what CI runs)
	$(SDD)/dial.py --check

test: ## run the whole test suite
	uv run pytest -q

dial: ## show each spec's stop and the gates it makes mandatory
	$(SDD)/dial.py

trace: ## REQ -> code -> test coverage
	$(SDD)/trace.py

trace-design: ## REQ -> design section coverage
	$(SDD)/trace.py --design

fresh: ## is each spec still true of the code it covers?
	$(SDD)/fresh.py

contract: ## contract tests both sides, then check the info.version bump
	uv run pytest tests/contract -q && $(SDD)/contract_diff.py

mutate: ## mutation testing on sdd.yaml mutation.targets; fails on unwaived survivors
	$(SDD)/mutate.py

evidence: ## write evidence/allowance-ledger/<sha>/
	$(SDD)/evidence.py allowance-ledger

land: ## scripted merge queue onto $(BASE) (make land BASE=demo/trunk)
	$(SDD)/land.py --base $(BASE)

board: ## create the GitHub Project, fields and task issues
	$(SDD)/board.py bootstrap

board-reset: ## put the board back to the demo-3 seed state
	$(SDD)/board.py reset
