.PHONY: install test etl-ipc etl-all build serve-dev clean

install:
	pip install -r requirements.txt

test:
	pytest etl/tests/ -v

etl-ipc:
	python -m etl.run --module ipc

etl-all:
	python -m etl.run --all

build:
	python scripts/build_site.py

serve-dev: build
	cd _site && python -m http.server 8000

clean:
	rm -rf __pycache__ .pytest_cache _site
	find . -type d -name __pycache__ -exec rm -rf {} +
