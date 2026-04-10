PYTHON ?= python

.PHONY: report report-strict test check

report:
	$(PYTHON) reporting.py

report-strict:
	$(PYTHON) reporting.py --fail-on-missing

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

check: test report-strict
