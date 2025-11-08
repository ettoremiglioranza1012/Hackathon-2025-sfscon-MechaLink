# Usa un’immagine Python leggera
FROM python:3.12-slim

# Imposta la directory di lavoro
WORKDIR /app

# Copia i requisiti e installali
RUN pip install fastapi psycopg[binary] pandas uvicorn


# Copia tutto il codice sorgente (main.py, ecc.)
COPY . .

# Espone la porta su cui gira l'API
EXPOSE 8000

# Comando di avvio
CMD ["uvicorn", "serving_layer:app", "--host", "0.0.0.0", "--port", "8000"]
