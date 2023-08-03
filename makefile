
build:
	python -m build

deploy: build
	twine upload dist/*

test:
	coverage run -m pytest
	coverage report -m

lint:
	mypy src/regfile_generics tests
	pylint src/regfile_generics --disable=fixme
	black --check .

html:
	+$(MAKE) -C docs html

.PHONY: build deploy tests
