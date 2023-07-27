
build:
	python -m build

deploy: build
	twine upload dist/*

test:
	coverage run -m pytest
	coverage report -m

lint:
	black --check .
	pylint src/regfile_generics --disable=fixme

.PHONY: build deploy tests
