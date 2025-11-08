SRC := src

.PHONY: build-app

build-app:
	docker compose up postgres &
	sleep 5
	uv run ./src/ingestion/create_table.py
	uv run ./src/ingestion/master_data.py
	uv run ./src/ingestion/fact_data.py
