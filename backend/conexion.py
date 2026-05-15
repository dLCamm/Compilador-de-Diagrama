from lexico import ErrorLexico, analizar_diagrama


def procesar_json(data):
    """Recibe el JSON del frontend e inicia el pipeline del compilador."""
    return procesar_lexico(data)


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
            "codigoC": None,
            "assembler": None,
            **(resultado or {}),
        },
    }
