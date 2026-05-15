# Analizador lexico del diagrama/JSON.

import re


class ErrorLexico(Exception):
    pass


# Patrones base inspirados en el analizador lexico de referencia.
# El orden importa: los operadores de dos caracteres deben evaluarse primero.
TOKEN_PATRONES = [
    ("KEYWORD", r"\b(if|else|while|return|int|float|void|bool|string|print|printf|println|for|true|false)\b"),
    ("STRING", r'"([^"\\]|\\.)*"'),
    ("NUMBER", r"\b\d+(\.\d+)?\b"),
    ("OPERATOR", r"==|!=|<=|>=|\+\+|--|&&|\|\||[+\-*/%=<>!]"),
    ("DELIMITER", r"[(),;{}]"),
    ("IDENTIFIER", r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"),
    ("WHITESPACE", r"\s+"),
]

PATRON_GENERAL = re.compile(
    "|".join(f"(?P<{token}>{patron})" for token, patron in TOKEN_PATRONES)
)


def identificar_tokens(texto):
    """Tokeniza una cadena de codigo o expresion."""
    tokens = []
    pos = 0
    texto = texto or ""

    while pos < len(texto):
        match = PATRON_GENERAL.match(texto, pos)
        if not match:
            raise ErrorLexico(f"Caracter no reconocido: {texto[pos]!r}")

        tipo = match.lastgroup
        valor = match.group(tipo)
        if tipo != "WHITESPACE":
            tokens.append((tipo, valor))
        pos = match.end()

    return tokens


def analizar_diagrama(data):
    """Extrae y tokeniza las partes compilables del JSON enviado por el frontend."""
    flow = data.get("flow", {})
    nodes = flow.get("nodes", [])

    if not isinstance(nodes, list):
        raise ErrorLexico("'flow.nodes' debe ser una lista.")

    resultado = []
    for node in nodes:
        node_type = node.get("type")
        node_data = node.get("data") or {}
        texto = _obtener_texto_compilable(node_type, node_data)

        if texto is None:
            continue

        resultado.append(
            {
                "nodeId": node.get("id"),
                "nodeType": node_type,
                "source": texto,
                "tokens": identificar_tokens(texto),
            }
        )

    return resultado


def _obtener_texto_compilable(node_type, node_data):
    if node_type == "input":
        variable = node_data.get("variable")
        data_type = node_data.get("dataType", "int")
        if variable:
            return f"{data_type} {variable}"
        return None

    if node_type in {"condition", "output", "process"}:
        return node_data.get("expression")

    return None
