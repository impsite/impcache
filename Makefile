build:
	docker compose build

mypy:
	docker compose run --no-deps --rm -it app mypy ./src

flake8:
	docker compose run --no-deps --rm -it app flake8 /app/src

pylint:
	docker compose run --no-deps --rm -it app pylint --recursive=y /app/src

black-check:
	docker compose run --no-deps --rm -it app black --line-length 120 --check /app/src

codestyle:
	make flake8
	make pylint
	make black-check

black:
	docker compose run --no-deps --rm -it app black --line-length 120 /app/src

test:
	docker compose run --rm -it app coverage run -m pytest -v

coverage:
	docker compose run --no-deps --rm -it app coverage report -m --fail-under 100

verify:
	make mypy
	make codestyle
	make test
	make coverage

build-python-package:
	docker compose run --no-deps --rm -it app bash -c "python -m build && chmod -R 755 ./dist"

pypi-publish:
	docker compose run --no-deps --rm -it app python -m twine upload -u="__token__" -p=$$PYPI_API_TOKEN dist/*
