PYTHON ?= python

.PHONY: report report-strict test self-check check

report:
	$(PYTHON) reporting.py

report-strict:
	$(PYTHON) reporting.py --fail-on-missing --fail-on-validation-issues --output artifacts/reporting_output.json --markdown-output artifacts/reporting_summary.md

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

self-check:
	$(PYTHON) self_check.py

check: self-check
