from generador import generar_assembler, generar_cpp
from lexico import ErrorLexico, analizar_diagrama
from semantico import ErrorSemantico, analizar_semantica
from sintactico_ast import ErrorSintactico, ParserAST


# Cache en memoria para que el frontend pueda cambiar entre pestanas
# C/assembler/echo sin reenviar el diagrama despues de compilar.
_ultima_compilacion = None
_ultimo_echo = None


def procesar_json(data):
    """Recibe el JSON del frontend y ejecuta lexico, sintactico y generacion."""
    respuesta = _procesar_compilacion(data)
    if respuesta["ok"]:
        _guardar_ultima_compilacion(respuesta)
    return respuesta


def procesar_codigo_c(data):
    """Compila el diagrama y devuelve solo la traduccion a C."""
    respuesta = _procesar_compilacion(data)
    if not respuesta["ok"]:
        return respuesta
    _guardar_ultima_compilacion(respuesta)
    return _respuesta(
        ok=True,
        stage="codigoC",
        mensaje="Traduccion a C generada correctamente.",
        warnings=respuesta["warnings"],
        resultado={
            "semantica": respuesta["resultado"]["semantica"],
            "codigoC": respuesta["resultado"]["codigoC"],
        },
    )


def procesar_assembler(data):
    """Compila el diagrama y devuelve solo la traduccion a assembler."""
    respuesta = _procesar_compilacion(data)
    if not respuesta["ok"]:
        return respuesta
    _guardar_ultima_compilacion(respuesta)
    return _respuesta(
        ok=True,
        stage="assembler",
        mensaje="Traduccion a assembler generada correctamente.",
        warnings=respuesta["warnings"],
        resultado={
            "semantica": respuesta["resultado"]["semantica"],
            "assembler": respuesta["resultado"]["assembler"],
        },
    )


def obtener_ultimo_codigo_c():
    if _ultima_compilacion is None:
        return _respuesta(
            ok=False,
            stage="codigoC",
            errores=["No hay una compilacion previa."],
        )
    return _respuesta(
        ok=True,
        stage="codigoC",
        mensaje="Ultima traduccion a C.",
        resultado={
            "codigoC": _ultima_compilacion["resultado"]["codigoC"],
        },
    )


def obtener_ultimo_assembler():
    if _ultima_compilacion is None:
        return _respuesta(
            ok=False,
            stage="assembler",
            errores=["No hay una compilacion previa."],
        )
    return _respuesta(
        ok=True,
        stage="assembler",
        mensaje="Ultima traduccion a assembler.",
        resultado={
            "assembler": _ultima_compilacion["resultado"]["assembler"],
        },
    )


def procesar_echo(data):
    """Compila el diagrama y devuelve el detalle de las fases ejecutadas."""
    respuesta = _procesar_compilacion(data)
    if respuesta["ok"]:
        _guardar_ultima_compilacion(respuesta)
    return _respuesta(
        ok=respuesta["ok"],
        stage="echo",
        mensaje="Echo de compilacion generado." if respuesta["ok"] else "Echo de compilacion con errores.",
        errores=respuesta["errores"],
        warnings=respuesta["warnings"],
        resultado={
            "echo": respuesta["resultado"].get("echo"),
            "codigoC": respuesta["resultado"].get("codigoC"),
            "assembler": respuesta["resultado"].get("assembler"),
        },
    )


def obtener_ultimo_echo():
    if _ultimo_echo is None:
        return _respuesta(
            ok=False,
            stage="echo",
            errores=["No hay una compilacion previa."],
        )
    return _respuesta(
        ok=True,
        stage="echo",
        mensaje="Ultimo echo de compilacion.",
        resultado={
            "echo": _ultimo_echo,
        },
    )


def _procesar_compilacion(data):
    # Pipeline unico usado por /compilar, /traducir/c, /traducir/assembler y /echo.
    # Asi todos los endpoints generan resultados consistentes desde el mismo AST.
    echo = []
    try:
        echo.append(_paso_echo("estructura", "Validando estructura basica del JSON."))
        _validar_estructura_basica(data)
        echo.append(_paso_echo("estructura", "Estructura valida.", ok=True))

        echo.append(_paso_echo("lexico", "Ejecutando analisis lexico."))
        tokens = analizar_diagrama(data)
        echo.append(_paso_echo("lexico", "Analisis lexico completado.", ok=True, detalle={"tokens": tokens}))

        echo.append(_paso_echo("sintactico", "Construyendo AST desde nodes y edges."))
        ast = ParserAST().parse(data)
        ast_serializado = ast.serializar()
        echo.append(_paso_echo("sintactico", "AST construido correctamente.", ok=True, detalle={"ast": ast_serializado}))

        echo.append(_paso_echo("semantico", "Ejecutando analisis semantico."))
        semantica = analizar_semantica(ast)
        echo.append(_paso_echo("semantico", "Analisis semantico completado.", ok=True, detalle={"semantica": semantica}))

        echo.append(_paso_echo("generacion_c", "Generando codigo C."))
        codigo_cpp = generar_cpp(ast)
        echo.append(_paso_echo("generacion_c", "Codigo C generado correctamente.", ok=True, detalle={"codigoC": codigo_cpp}))

        echo.append(_paso_echo("generacion_assembler", "Generando codigo assembler."))
        assembler = generar_assembler(ast)
        echo.append(_paso_echo("generacion_assembler", "Codigo assembler generado correctamente.", ok=True, detalle={"assembler": assembler}))
    except ErrorLexico as error:
        mensaje = _mensaje_error_usuario(error, data)
        echo.append(_paso_echo("lexico", mensaje, ok=False))
        _guardar_ultimo_echo(echo)
        return _respuesta(ok=False, stage="lexico", errores=[mensaje], resultado={"echo": echo})
    except ErrorSintactico as error:
        mensaje = _mensaje_error_usuario(error, data)
        echo.append(_paso_echo("sintactico", mensaje, ok=False))
        _guardar_ultimo_echo(echo)
        return _respuesta(ok=False, stage="sintactico", errores=[mensaje], resultado={"echo": echo})
    except ErrorSemantico as error:
        mensaje = _mensaje_error_usuario(error, data)
        echo.append(_paso_echo("semantico", mensaje, ok=False))
        _guardar_ultimo_echo(echo)
        return _respuesta(ok=False, stage="semantico", errores=[mensaje], resultado={"echo": echo})
    except ValueError as error:
        mensaje = _mensaje_error_usuario(error, data)
        echo.append(_paso_echo("estructura", mensaje, ok=False))
        _guardar_ultimo_echo(echo)
        return _respuesta(ok=False, stage="estructura", errores=[mensaje], resultado={"echo": echo})

    respuesta = _respuesta(
        ok=True,
        stage="compilacion",
        mensaje="Compilacion completada correctamente.",
        resultado={
            "tokens": tokens,
            "ast": ast_serializado,
            "semantica": semantica,
            "codigoC": codigo_cpp,
            "assembler": assembler,
            "echo": echo,
        },
        warnings=semantica.get("warnings", []),
    )
    _guardar_ultimo_echo(echo)
    return respuesta


def _guardar_ultima_compilacion(respuesta):
    global _ultima_compilacion
    _ultima_compilacion = respuesta


def _guardar_ultimo_echo(echo):
    global _ultimo_echo
    _ultimo_echo = echo


def _mensaje_error_usuario(error, data):
    mensaje = str(error)
    for node_id, nombre in _mapa_nombres_figuras(data).items():
        reemplazos = {
            f"nodo '{node_id}'": f"figura '{nombre}'",
            f"nodo {node_id}": f"figura '{nombre}'",
            f"Nodo '{node_id}'": f"Figura '{nombre}'",
            f"Nodo {node_id}": f"Figura '{nombre}'",
            f"condicion '{node_id}'": f"condicion '{nombre}'",
            f"'{node_id}'": f"'{nombre}'" if len(node_id) > 12 else f"'{node_id}'",
        }
        for original, reemplazo in reemplazos.items():
            mensaje = mensaje.replace(original, reemplazo)
    return mensaje.replace("nodo", "figura").replace("Nodo", "Figura")


def _mapa_nombres_figuras(data):
    flow = data.get("flow", {}) if isinstance(data, dict) else {}
    nodes = flow.get("nodes", []) if isinstance(flow, dict) else []
    return {
        node.get("id"): _nombre_figura(node)
        for node in nodes
        if isinstance(node, dict) and node.get("id")
    }


def _nombre_figura(node):
    data = node.get("data") or {}
    node_type = node.get("type")
    if node_type == "process":
        return data.get("code") or data.get("label") or "Proceso"
    if node_type == "condition":
        return data.get("expression") or data.get("label") or "Condicion"
    if node_type == "input":
        variable = data.get("variable") or data.get("label")
        return f"Entrada {variable}" if variable else "Entrada"
    if node_type == "output":
        expression = data.get("expression") or data.get("label")
        return f"Salida {expression}" if expression else "Salida"
    return data.get("label") or node_type or "figura"


def _paso_echo(stage, mensaje, ok=None, detalle=None):
    # Formato comun para la pestana Echo del frontend.
    paso = {
        "stage": stage,
        "mensaje": mensaje,
    }
    if ok is not None:
        paso["ok"] = ok
    if detalle is not None:
        paso["detalle"] = detalle
    return paso


def procesar_lexico(data):
    """Ejecuta solo la fase lexica sobre el JSON del diagrama."""
    try:
        _validar_estructura_basica(data)
        tokens = analizar_diagrama(data)
    except (ErrorLexico, ValueError) as error:
        return _respuesta(
            ok=False,
            stage="lexico",
            errores=[str(error)],
        )

    return _respuesta(
        ok=True,
        stage="lexico",
        mensaje="Analisis lexico completado correctamente.",
        resultado={
            "tokens": tokens,
        },
    )


def _validar_estructura_basica(data):
    # Validacion del contrato minimo que debe mandar ReactFlow:
    # flow.nodes y flow.edges con ids y conexiones source/target.
    if not isinstance(data, dict):
        raise ValueError("El cuerpo de la peticion debe ser un objeto JSON.")

    flow = data.get("flow")
    if not isinstance(flow, dict):
        raise ValueError("El JSON debe incluir un objeto 'flow'.")

    nodes = flow.get("nodes")
    edges = flow.get("edges")
    if not isinstance(nodes, list):
        raise ValueError("'flow.nodes' debe ser una lista.")
    if not isinstance(edges, list):
        raise ValueError("'flow.edges' debe ser una lista.")

    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise ValueError(f"El nodo en posicion {index} debe ser un objeto.")
        if not node.get("id"):
            raise ValueError(f"El nodo en posicion {index} no tiene 'id'.")
        if not node.get("type"):
            raise ValueError(f"El nodo '{node.get('id')}' no tiene 'type'.")
        if not isinstance(node.get("data", {}), dict):
            raise ValueError(f"El nodo '{node.get('id')}' debe tener 'data' como objeto.")

    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            raise ValueError(f"El edge en posicion {index} debe ser un objeto.")
        if not edge.get("id"):
            raise ValueError(f"El edge en posicion {index} no tiene 'id'.")
        if not edge.get("source"):
            raise ValueError(f"El edge '{edge.get('id')}' no tiene 'source'.")
        if not edge.get("target"):
            raise ValueError(f"El edge '{edge.get('id')}' no tiene 'target'.")


def _respuesta(ok, stage, mensaje=None, errores=None, warnings=None, resultado=None):
    return {
        "ok": ok,
        "stage": stage,
        "mensaje": mensaje or ("OK" if ok else "El diagrama tiene errores."),
        "errores": errores or [],
        "warnings": warnings or [],
        "resultado": {
            "tokens": None,
            "ast": None,
            "semantica": None,
            "codigoC": None,
            "assembler": None,
            **(resultado or {}),
        },
    }
