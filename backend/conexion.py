def procesar_json(data):
    """Recibe el JSON del frontend y prepara una respuesta base."""
    return {
        "ok": True,
        "mensaje": "JSON recibido correctamente",
        "errores": [],
        "data": data,
        "ast": None,
    }
