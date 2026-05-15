from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from conexion import procesar_json, procesar_lexico


app = FastAPI(title="Backend Compilador de Diagrama")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def inicio():
    return {"mensaje": "Backend del compilador funcionando"}


@app.post("/compilar")
def compilar(data: dict):
    return procesar_json(data)


@app.post("/lexico")
def lexico(data: dict):
    return procesar_lexico(data)
