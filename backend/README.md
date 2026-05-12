# Backend - Estructura simple

Estructura minima para trabajar el compilador por etapas.

```text
backend/
├── main.py              # Punto de entrada del backend
├── conexion.py          # Recibe el JSON del frontend y manda la respuesta
├── lexico.py            # Analisis lexico del diagrama/JSON
├── sintactico_ast.py    # Parser que construye el AST y clases NodoAST
└── semantico.py         # Analisis semantico del AST: variables, tipos y reglas
```

Idea de flujo:

```text
frontend -> conexion.py -> lexico.py -> sintactico_ast.py -> semantico.py
```

La estructura esta basada en el compilador de referencia:

```text
lexico.py
sintactico_ast.py
semantico.py
```

Para este proyecto se agregan los archivos de conexion:

```text
main.py
conexion.py
```

El backend deberia trabajar internamente con un AST. El JSON puede cambiar, pero la idea es convertirlo a nodos propios del compilador dentro de `sintactico_ast.py`.

```text
JSON del frontend
   ↓
tokens / instrucciones
   ↓
AST con nodos
   ↓
validacion semantica
```

## Entorno virtual y dependencias

Para trabajar el backend se recomienda usar un entorno virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Dependencias iniciales:

```text
fastapi
uvicorn
```

`fastapi` sirve para crear la API que recibe el JSON enviado por el frontend.

`uvicorn` sirve para levantar el servidor local donde corre esa API.

Ejemplo de uso futuro:

```text
frontend manda JSON -> FastAPI lo recibe -> conexion.py inicia el flujo del compilador
```
