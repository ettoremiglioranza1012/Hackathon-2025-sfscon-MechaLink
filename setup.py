import logging

logging.basicConfig(filename="myapp.log", level=logging.INFO, force=True)
key = input("Insert your API key here: ")

with open("./streamlit_app/.env", "w") as f:
    logging.info("Writing .env")
    f.write(f"API_KEY={key}")

logging.info("Successul! .env correctly created.")
