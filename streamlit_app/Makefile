build-image: app.py
	docker build -t streamlit_app .

.PHONY: run-app
run-app:
	docker run -p 8501:8501 streamlit_app

