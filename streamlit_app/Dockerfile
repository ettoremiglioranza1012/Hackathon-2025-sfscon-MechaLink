FROM python:3.12

WORKDIR /app

# copy everything from host
COPY . .

RUN pip install -r requirements.txt

# run app from localhost on port 8501
ENTRYPOINT [ "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]

