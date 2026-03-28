# Tower Defense RL environment workflow

# install deps
.PHONY: i
i:
	python -m pip install --upgrade pip
	python -m pip install -r requirements.txt
	python -m pip install pytest

# run tests
.PHONY: test
test:
	python tests/test_environment.py

# run all (install + tests)
.PHONY: all
all: i test

# quick check
.PHONY: check
check:
	python tests/test_environment.py
