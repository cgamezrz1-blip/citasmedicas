from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"mensaje": "API Actualizada"}

@app.get("/prueba")
def evento_prueba():
    return {"eventos": ["city js", "devops day", "epam talks"]}
