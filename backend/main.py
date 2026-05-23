from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from conexion import (
    obtener_ultimo_assembler,
    obtener_ultimo_codigo_c,
    obtener_ultimo_echo,
    procesar_assembler,
    procesar_codigo_c,
    procesar_echo,
    procesar_json,
    procesar_lexico,
)


app = FastAPI(title="Backend Compilador de Diagrama")

# API consumida por el frontend local de Vite.
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
    # Endpoint principal: devuelve tokens, AST, C, assembler y echo.
    return procesar_json(data)


@app.post("/traducir/c")
def traducir_c(data: dict):
    # Para la pestana donde solo se necesita mostrar el codigo C.
    return procesar_codigo_c(data)


@app.post("/traducir/assembler")
def traducir_assembler(data: dict):
    # Para la pestana donde solo se necesita mostrar assembler.
    return procesar_assembler(data)


@app.get("/ultimo/c")
def ultimo_c():
    # Recupera la ultima traduccion sin reenviar el diagrama.
    return obtener_ultimo_codigo_c()


@app.get("/ultimo/assembler")
def ultimo_assembler():
    # Recupera el ultimo assembler sin reenviar el diagrama.
    return obtener_ultimo_assembler()


@app.post("/echo")
def echo(data: dict):
    # Devuelve el detalle de fases para la pestana Echo.
    return procesar_echo(data)


@app.get("/ultimo/echo")
def ultimo_echo():
    # Recupera el ultimo echo generado.
    return obtener_ultimo_echo()


@app.post("/lexico")
def lexico(data: dict):
    return procesar_lexico(data)
