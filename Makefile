SRC := src

.PHONY: build-app run-app clean-app

build-app:
	docker compose up -d postgres
	@sleep 5
	uv run ./src/ingestion/create_table.py
	uv run ./src/ingestion/master_data.py
	uv run ./src/ingestion/fact_data.py
	uv run ./src/ingestion/last_ingestion.py
	docker compose up --build

run-app:
	docker compose up

# cleans the directory and is often useful to execute this 
# to troubleshoot some errors related to postgres.
clean-app:
	rm -rf data
