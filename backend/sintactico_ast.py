from lexico import identificar_tokens


class ErrorSintactico(Exception):
    pass


def indentar_codigo(codigo, espacios=4):
    indentacion = " " * espacios
    return "\n".join(indentacion + linea if linea else linea for linea in codigo.splitlines())


def _bloque_c(encabezado, instrucciones):
    cuerpo = "\n".join(indentar_codigo(i.traducirCpp()) for i in instrucciones) or "    ;"
    return f"{encabezado}\n{{\n{cuerpo}\n}}"


def _precedencia_operador(operador):
    # Mantiene la precedencia al reconstruir expresiones como (a + b) * 2.
    precedencias = {
        "||": 1,
        "&&": 2,
        "==": 3,
        "!=": 3,
        "<": 4,
        ">": 4,
        "<=": 4,
        ">=": 4,
        "+": 5,
        "-": 5,
        "*": 6,
        "/": 6,
        "%": 6,
    }
    return precedencias.get(operador, 0)


def _tipo_c(tipo):
    # Ajustes minimos porque el lenguaje destino es C, no C++.
    if tipo == "string":
        return "char"
    if tipo == "bool":
        return "int"
    return tipo


def _formato_printf(nodo):
    # Decide el especificador de printf segun el nodo o el tipo recolectado.
    if isinstance(nodo, NodoCadena):
        return None
    if isinstance(nodo, NodoNumero):
        return "%f" if "." in nodo.valor[1] else "%d"
    if isinstance(nodo, NodoIdentificador):
        tipo = NodoAST.tipos_variables.get(nodo.nombre[1], "int")
        return "%s" if tipo == "string" else "%f" if tipo in {"float", "double"} else "%d"
    return "%d"


class NodoAST:
    # Clase base para todos los nodos del AST.
    tipos_variables = {}
    contador_etiquetas = 0

    @classmethod
    def nueva_etiqueta(cls, nombre):
        cls.contador_etiquetas += 1
        return f"{nombre}_{cls.contador_etiquetas}"

    def traducirCpp(self):
        raise NotImplementedError("Metodo traducirCpp() no implementado en este Nodo.")

    def generarCodigo(self):
        raise NotImplementedError("Metodo generarCodigo() no implementado en este Nodo.")

    def serializar(self):
        return {"tipo": type(self).__name__}


class NodoPrograma(NodoAST):
    # Nodo que representa el programa completo creado desde el diagrama.
    def __init__(self, instrucciones, language_target="cpp", node_id="programa", label="Programa"):
        self.node_id = node_id
        self.label = label
        self.language_target = language_target
        self.instrucciones = instrucciones
        self.variables = []

    def traducirCpp(self):
        # Aunque el metodo conserva el nombre historico traducirCpp,
        # aqui se genera C real con stdio.h, scanf y printf.
        self.variables = self._recolectar_variables(self.instrucciones)
        NodoAST.tipos_variables = {nombre: tipo for tipo, nombre in self.variables}

        includes = ["#include <stdio.h>"]
        if self._usa_tipo("string"):
            includes.append("#include <string.h>")

        cuerpo = "\n".join(
            indentar_codigo(i.traducirCpp())
            for i in self.instrucciones
            if not isinstance(i, NodoFin)
        )
        return "\n".join([
            *includes,
            "",
            "int main()",
            "{",
            cuerpo,
            "    return 0;",
            "}",
        ])

    def generarCodigo(self):
        # Estructura base del assembler siguiendo el ejemplo de referencia.
        NodoAST.contador_etiquetas = 0
        self.variables = self._recolectar_variables(self.instrucciones)
        data = ["section .data", "    newline: db 10", "    dot: db '.'"]
        bss = ["section .bss", "    print_buffer: resb 32"]
        for tipo, nombre in self.variables:
            if tipo in ("int", "float", "double", "bool"):
                bss.append(f"    {nombre}:    resd 1")

        codigo = ["section .text", "global _start", "_start:"]
        codigo.extend(i.generarCodigo() for i in self.instrucciones if not isinstance(i, NodoFin))
        codigo.extend([
            "    ; terminar programa",
            "    mov eax, 1",
            "    mov ebx, 0",
            "    int 0x80",
        ])
        return "\n".join(data + bss + codigo)

    def serializar(self):
        return {
            "tipo": "NodoPrograma",
            "node_id": self.node_id,
            "label": self.label,
            "language_target": self.language_target,
            "instrucciones": [i.serializar() for i in self.instrucciones],
        }

    def _usa_tipo(self, tipo):
        return any(variable_tipo == tipo for variable_tipo, _ in self._recolectar_variables(self.instrucciones))

    def _recolectar_variables(self, instrucciones):
        # Recorre tambien ramas y ciclos para declarar variables en .bss
        # y para saber que formato usar en printf/scanf.
        variables = []
        vistas = set()
        pendientes = list(instrucciones)
        while pendientes:
            instruccion = pendientes.pop(0)
            if isinstance(instruccion, NodoEntrada):
                variable = (instruccion.tipo[1], instruccion.nombre[1])
                if variable not in vistas:
                    variables.append(variable)
                    vistas.add(variable)
            elif isinstance(instruccion, NodoAsignacion) and instruccion.tipo is not None:
                variable = (instruccion.tipo[1], instruccion.nombre[1])
                if variable not in vistas:
                    variables.append(variable)
                    vistas.add(variable)
            elif isinstance(instruccion, NodoIf):
                pendientes.extend(instruccion.cuerpo)
                pendientes.extend(instruccion.sino or [])
            elif isinstance(instruccion, NodoWhile):
                pendientes.extend(instruccion.cuerpo)
            elif isinstance(instruccion, NodoFor):
                pendientes.append(instruccion.init)
                pendientes.append(instruccion.incremento)
                pendientes.extend(instruccion.cuerpo)
        return variables


class NodoEntrada(NodoAST):
    # Nodo que representa una lectura de variable.
    def __init__(self, tipo, nombre, node_id="", label=""):
        self.tipo = tipo
        self.nombre = nombre
        self.node_id = node_id
        self.label = label

    def traducirCpp(self):
        # "Leer edad" termina como declaracion C + scanf.
        tipo = self.tipo[1]
        nombre = self.nombre[1]
        if tipo == "string":
            return f"char {nombre}[256];\nscanf(\"%255s\", {nombre});"
        formatos = {
            "int": "%d",
            "bool": "%d",
            "float": "%f",
            "double": "%lf",
        }
        return f"{_tipo_c(tipo)} {nombre};\nscanf(\"{formatos.get(tipo, '%d')}\", &{nombre});"

    def generarCodigo(self):
        return f"    ; entrada: leer {self.nombre[1]}"

    def serializar(self):
        return {
            "tipo": "NodoEntrada",
            "node_id": self.node_id,
            "label": self.label,
            "data_type": self.tipo[1],
            "variable": self.nombre[1],
        }


class NodoAsignacion(NodoAST):
    # Nodo que representa declaracion/asignacion de variables.
    def __init__(self, tipo, nombre, expresion, node_id="", label=""):
        self.tipo = tipo
        self.nombre = nombre
        self.expresion = expresion
        self.node_id = node_id
        self.label = label

    def traducirCpp(self):
        # Las asignaciones string usan arreglos char y strcpy cuando ya existen.
        if self.tipo is not None and self.tipo[1] == "string":
            return f"char {self.nombre[1]}[256] = {self.expresion.traducirCpp()};"
        if self.tipo is None and NodoAST.tipos_variables.get(self.nombre[1]) == "string":
            return f"strcpy({self.nombre[1]}, {self.expresion.traducirCpp()});"
        prefijo = f"{_tipo_c(self.tipo[1])} " if self.tipo is not None else ""
        return f"{prefijo}{self.nombre[1]} = {self.expresion.traducirCpp()};"

    def generarCodigo(self):
        codigo = [self.expresion.generarCodigo()]
        codigo.append(f"    mov [{self.nombre[1]}], eax")
        return "\n".join(codigo)

    def serializar(self):
        return {
            "tipo": "NodoAsignacion",
            "node_id": self.node_id,
            "label": self.label,
            "data_type": self.tipo[1] if self.tipo else None,
            "variable": self.nombre[1],
            "expresion": self.expresion.serializar(),
        }


class NodoProceso(NodoAST):
    # Nodo de respaldo cuando el proceso no es una asignacion parseable.
    def __init__(self, expresion, node_id="", label=""):
        self.expresion = expresion
        self.node_id = node_id
        self.label = label

    def traducirCpp(self):
        expresion = self.expresion.strip()
        return expresion if expresion.endswith(";") else f"{expresion};"

    def generarCodigo(self):
        return f"    ; proceso: {self.expresion}"

    def serializar(self):
        return {
            "tipo": "NodoProceso",
            "node_id": self.node_id,
            "label": self.label,
            "expresion": self.expresion,
        }


class NodoFin(NodoAST):
    def __init__(self, node_id="", label=""):
        self.node_id = node_id
        self.label = label

    def traducirCpp(self):
        return ""

    def generarCodigo(self):
        return "    ; fin"

    def serializar(self):
        return {"tipo": "NodoFin", "node_id": self.node_id, "label": self.label}


class NodoIf(NodoAST):
    # Nodo que representa una decision con dos ramas.
    def __init__(self, condicion, cuerpo, sino=None, node_id="", label=""):
        self.condicion = condicion
        self.cuerpo = cuerpo
        self.sino = sino or []
        self.node_id = node_id
        self.label = label

    def traducirCpp(self):
        cuerpo = "\n".join(indentar_codigo(c.traducirCpp()) for c in self.cuerpo) or "    ;"
        if len(self.sino) == 1 and isinstance(self.sino[0], NodoIf):
            else_if = self.sino[0].traducirCpp()
            return (
                f"if({self.condicion.traducirCpp()})\n"
                "{\n"
                f"{cuerpo}\n"
                "}\n"
                f"else {else_if}"
            )

        sino = "\n".join(indentar_codigo(c.traducirCpp()) for c in self.sino) or "    ;"
        return (
            f"if({self.condicion.traducirCpp()})\n"
            "{\n"
            f"{cuerpo}\n"
            "}\n"
            "else\n"
            "{\n"
            f"{sino}\n"
            "}"
        )

    def generarCodigo(self):
        numero = NodoAST.contador_etiquetas + 1
        NodoAST.contador_etiquetas = numero
        etiqueta_sino = f"sino_{numero}"
        etiqueta_fin = f"fin_si_{numero}"
        codigo = [self.condicion.generarCodigo(), "    cmp eax, 0", f"    je {etiqueta_sino}"]
        codigo.extend(instruccion.generarCodigo() for instruccion in self.cuerpo)
        codigo.append(f"    jmp {etiqueta_fin}")
        codigo.append(f"{etiqueta_sino}:")
        codigo.extend(instruccion.generarCodigo() for instruccion in self.sino)
        codigo.append(f"{etiqueta_fin}:")
        return "\n".join(codigo)

    def serializar(self):
        return {
            "tipo": "NodoIf",
            "node_id": self.node_id,
            "label": self.label,
            "condicion": self.condicion.serializar(),
            "cuerpo": [i.serializar() for i in self.cuerpo],
            "sino": [i.serializar() for i in self.sino],
        }


class NodoWhile(NodoAST):
    # Nodo que representa un ciclo cuando una rama vuelve a la condicion.
    def __init__(self, condicion, cuerpo, node_id="", label=""):
        self.condicion = condicion
        self.cuerpo = cuerpo
        self.node_id = node_id
        self.label = label

    def traducirCpp(self):
        return _bloque_c(f"while({self.condicion.traducirCpp()})", self.cuerpo)

    def generarCodigo(self):
        numero = NodoAST.contador_etiquetas + 1
        NodoAST.contador_etiquetas = numero
        etiqueta_inicio = f"mientras_{numero}"
        etiqueta_fin = f"fin_mientras_{numero}"
        codigo = [f"{etiqueta_inicio}:", self.condicion.generarCodigo(), "    cmp eax, 0", f"    je {etiqueta_fin}"]
        codigo.extend(instruccion.generarCodigo() for instruccion in self.cuerpo)
        codigo.append(f"    jmp {etiqueta_inicio}")
        codigo.append(f"{etiqueta_fin}:")
        return "\n".join(codigo)

    def serializar(self):
        return {
            "tipo": "NodoWhile",
            "node_id": self.node_id,
            "label": self.label,
            "condicion": self.condicion.serializar(),
            "cuerpo": [i.serializar() for i in self.cuerpo],
        }


class NodoFor(NodoAST):
    # Nodo que representa un ciclo for inferido desde el diagrama.
    def __init__(self, init, condicion, incremento, cuerpo, node_id="", label=""):
        self.init = init
        self.condicion = condicion
        self.incremento = incremento
        self.cuerpo = cuerpo
        self.node_id = node_id
        self.label = label

    def traducirCpp(self):
        # El for se infiere de: init -> condition -> cuerpo -> incremento -> condition.
        if isinstance(self.init, NodoAsignacion) and self.init.tipo is not None:
            tipo = _tipo_c(self.init.tipo[1])
            nombre = self.init.nombre[1]
            valor = self.init.expresion.traducirCpp()
            declaracion = f"{tipo} {nombre};"
            init = f"{nombre} = {valor}"
        else:
            declaracion = ""
            init = self.init.traducirCpp().rstrip(";")
        incremento = self.incremento.traducirCpp().rstrip(";")
        ciclo = _bloque_c(f"for({init}; {self.condicion.traducirCpp()}; {incremento})", self.cuerpo)
        return f"{declaracion}\n{ciclo}" if declaracion else ciclo

    def generarCodigo(self):
        numero = NodoAST.contador_etiquetas + 1
        NodoAST.contador_etiquetas = numero
        etiqueta_inicio = f"para_{numero}"
        etiqueta_fin = f"fin_para_{numero}"
        codigo = [
            self.init.generarCodigo(),
            f"{etiqueta_inicio}:",
            self.condicion.generarCodigo(),
            "    cmp eax, 0",
            f"    je {etiqueta_fin}",
        ]
        codigo.extend(instruccion.generarCodigo() for instruccion in self.cuerpo)
        codigo.append(self.incremento.generarCodigo())
        codigo.append(f"    jmp {etiqueta_inicio}")
        codigo.append(f"{etiqueta_fin}:")
        return "\n".join(codigo)

    def serializar(self):
        return {
            "tipo": "NodoFor",
            "node_id": self.node_id,
            "label": self.label,
            "init": self.init.serializar(),
            "condicion": self.condicion.serializar(),
            "incremento": self.incremento.serializar(),
            "cuerpo": [i.serializar() for i in self.cuerpo],
        }


class NodoPrint(NodoAST):
    # Nodo que representa una salida.
    def __init__(self, argumentos, node_id="", label="", salto_linea=True):
        self.argumentos = argumentos
        self.node_id = node_id
        self.label = label
        self.salto_linea = salto_linea

    def traducirCpp(self):
        # "Mostrar x" termina como printf con el formato correcto.
        if not self.argumentos:
            return 'printf("\\n");' if self.salto_linea else 'printf("");'

        if len(self.argumentos) == 1 and isinstance(self.argumentos[0], NodoCadena):
            texto = self.argumentos[0].valor[1]
            if self.salto_linea:
                texto = texto[:-1] + "\\n" + texto[-1]
            return f"printf({texto});"

        formatos = []
        valores = []
        for argumento in self.argumentos:
            formato = _formato_printf(argumento)
            if formato is None:
                formatos.append("%s")
            else:
                formatos.append(formato)
            valores.append(argumento.traducirCpp())

        salto = "\\n" if self.salto_linea else ""
        return f'printf("{" ".join(formatos)}{salto}",{", ".join(valores)});'

    def generarCodigo(self):
        args = ", ".join(a.traducirCpp() for a in self.argumentos)
        return f"    ; salida: mostrar {args}"

    def serializar(self):
        return {
            "tipo": "NodoPrint",
            "node_id": self.node_id,
            "label": self.label,
            "salto_linea": self.salto_linea,
            "argumentos": [a.serializar() for a in self.argumentos],
        }


class NodoOperacion(NodoAST):
    # Nodo que representa una operacion binaria.
    def __init__(self, izquierda, operador, derecha):
        self.izquierda = izquierda
        self.operador = operador
        self.derecha = derecha

    def traducirCpp(self):
        izquierda = self._traducir_hijo(self.izquierda)
        derecha = self._traducir_hijo(self.derecha, derecha=True)
        return f"{izquierda} {self.operador[1]} {derecha}"

    def generarCodigo(self):
        codigo = [
            self.izquierda.generarCodigo(),
            "    push eax",
            self.derecha.generarCodigo(),
            "    mov ebx, eax",
            "    pop eax",
        ]
        aritmeticos = {
            "+": "    add eax, ebx",
            "-": "    sub eax, ebx",
            "*": "    imul eax, ebx",
        }
        relacionales = {
            ">": "setg",
            "<": "setl",
            ">=": "setge",
            "<=": "setle",
            "==": "sete",
            "!=": "setne",
        }
        if self.operador[1] in aritmeticos:
            codigo.append(aritmeticos[self.operador[1]])
        elif self.operador[1] == "/":
            codigo.extend(["    cdq", "    idiv ebx"])
        elif self.operador[1] in relacionales:
            codigo.extend(["    cmp eax, ebx", f"    {relacionales[self.operador[1]]} al", "    movzx eax, al"])
        elif self.operador[1] in {"&&", "||"}:
            codigo.append(f"    ; operador logico {self.operador[1]}")
        else:
            codigo.append(f"    ; operador no implementado: {self.operador[1]}")
        return "\n".join(codigo)

    def serializar(self):
        return {
            "tipo": "NodoOperacion",
            "operador": self.operador[1],
            "izquierda": self.izquierda.serializar(),
            "derecha": self.derecha.serializar(),
        }

    def _traducir_hijo(self, hijo, derecha=False):
        texto = hijo.traducirCpp()
        if not isinstance(hijo, NodoOperacion):
            return texto
        precedencia_hijo = _precedencia_operador(hijo.operador[1])
        precedencia_actual = _precedencia_operador(self.operador[1])
        necesita_parentesis = precedencia_hijo < precedencia_actual
        if derecha and self.operador[1] in {"-", "/", "%"} and precedencia_hijo == precedencia_actual:
            necesita_parentesis = True
        return f"({texto})" if necesita_parentesis else texto


class NodoUnario(NodoAST):
    # Nodo que representa operadores unarios como !x o -x.
    def __init__(self, operador, expresion):
        self.operador = operador
        self.expresion = expresion

    def traducirCpp(self):
        expresion = self.expresion.traducirCpp()
        if isinstance(self.expresion, NodoOperacion):
            expresion = f"({expresion})"
        return f"{self.operador[1]}{expresion}"

    def generarCodigo(self):
        codigo = [self.expresion.generarCodigo()]
        if self.operador[1] == "-":
            codigo.append("    neg eax")
        elif self.operador[1] == "!":
            codigo.extend(["    cmp eax, 0", "    sete al", "    movzx eax, al"])
        return "\n".join(codigo)

    def serializar(self):
        return {
            "tipo": "NodoUnario",
            "operador": self.operador[1],
            "expresion": self.expresion.serializar(),
        }


class NodoLlamadaFuncion(NodoAST):
    # Nodo que representa una llamada simple tipo f(a, 1).
    def __init__(self, nombre_funcion, argumentos):
        self.nombre_funcion = nombre_funcion
        self.argumentos = argumentos

    def traducirCpp(self):
        args = ", ".join(a.traducirCpp() for a in self.argumentos)
        return f"{self.nombre_funcion}({args})"

    def generarCodigo(self):
        return f"    ; llamada a funcion {self.traducirCpp()}"

    def serializar(self):
        return {
            "tipo": "NodoLlamadaFuncion",
            "nombre_funcion": self.nombre_funcion,
            "argumentos": [a.serializar() for a in self.argumentos],
        }


class NodoIdentificador(NodoAST):
    # Nodo que representa a un identificador.
    def __init__(self, nombre):
        self.nombre = nombre

    def traducirCpp(self):
        return self.nombre[1]

    def generarCodigo(self):
        return f"    mov eax, [{self.nombre[1]}]"

    def serializar(self):
        return {"tipo": "NodoIdentificador", "nombre": self.nombre[1]}


class NodoNumero(NodoAST):
    # Nodo que representa a un numero.
    def __init__(self, valor):
        self.valor = valor

    def traducirCpp(self):
        return self.valor[1]

    def generarCodigo(self):
        return f"    mov eax, {self.valor[1]}"

    def serializar(self):
        return {"tipo": "NodoNumero", "valor": self.valor[1]}


class NodoCadena(NodoAST):
    # Nodo que representa a una cadena.
    def __init__(self, valor):
        self.valor = valor

    def traducirCpp(self):
        return self.valor[1]

    def generarCodigo(self):
        return f"    ; cadena {self.valor[1]}"

    def serializar(self):
        return {"tipo": "NodoCadena", "valor": self.valor[1]}


class NodoBooleano(NodoAST):
    # Nodo que representa true/false.
    def __init__(self, valor):
        self.valor = valor

    def traducirCpp(self):
        return self.valor[1]

    def generarCodigo(self):
        return "    mov eax, 1" if self.valor[1] == "true" else "    mov eax, 0"

    def serializar(self):
        return {"tipo": "NodoBooleano", "valor": self.valor[1]}


class ParserExpresion:
    # Parser por precedencia, inspirado en el Parser de referencia.
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def obtener_token_actual(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def coincidir(self, tipo_esperado, valor_esperado=None):
        token_actual = self.obtener_token_actual()
        if token_actual and token_actual[0] == tipo_esperado:
            if valor_esperado is None or token_actual[1] == valor_esperado:
                self.pos += 1
                return token_actual
        esperado = f"{tipo_esperado} {valor_esperado}" if valor_esperado else tipo_esperado
        raise ErrorSintactico(f"Error sintactico: se esperaba {esperado}, pero se encontro: {token_actual}")

    def parsear(self):
        if not self.tokens:
            raise ErrorSintactico("Expresion vacia.")
        expresion = self.expresion()
        if self.obtener_token_actual() is not None:
            raise ErrorSintactico(f"Token inesperado al final de expresion: {self.obtener_token_actual()}")
        return expresion

    def expresion(self):
        # Punto de entrada de la gramatica de expresiones.
        return self.logico_or()

    def logico_or(self):
        izquierda = self.logico_and()
        while self._valor_actual("||"):
            operador = self.coincidir("OPERATOR")
            derecha = self.logico_and()
            izquierda = NodoOperacion(izquierda, operador, derecha)
        return izquierda

    def logico_and(self):
        izquierda = self.igualdad()
        while self._valor_actual("&&"):
            operador = self.coincidir("OPERATOR")
            derecha = self.igualdad()
            izquierda = NodoOperacion(izquierda, operador, derecha)
        return izquierda

    def igualdad(self):
        izquierda = self.comparacion()
        while self._valor_actual("==") or self._valor_actual("!="):
            operador = self.coincidir("OPERATOR")
            derecha = self.comparacion()
            izquierda = NodoOperacion(izquierda, operador, derecha)
        return izquierda

    def comparacion(self):
        izquierda = self.termino()
        while self._valor_actual("<") or self._valor_actual(">") or self._valor_actual("<=") or self._valor_actual(">="):
            operador = self.coincidir("OPERATOR")
            derecha = self.termino()
            izquierda = NodoOperacion(izquierda, operador, derecha)
        return izquierda

    def termino(self):
        izquierda = self.factor()
        while self._valor_actual("+") or self._valor_actual("-"):
            operador = self.coincidir("OPERATOR")
            derecha = self.factor()
            izquierda = NodoOperacion(izquierda, operador, derecha)
        return izquierda

    def factor(self):
        izquierda = self.unario()
        while self._valor_actual("*") or self._valor_actual("/") or self._valor_actual("%"):
            operador = self.coincidir("OPERATOR")
            derecha = self.unario()
            izquierda = NodoOperacion(izquierda, operador, derecha)
        return izquierda

    def unario(self):
        if self._valor_actual("!") or self._valor_actual("-"):
            operador = self.coincidir("OPERATOR")
            return NodoUnario(operador, self.unario())
        return self.primario()

    def primario(self):
        token = self.obtener_token_actual()
        if token is None:
            raise ErrorSintactico("Expresion incompleta.")
        if token[0] == "NUMBER":
            return NodoNumero(self.coincidir("NUMBER"))
        if token[0] == "STRING":
            return NodoCadena(self.coincidir("STRING"))
        if token[0] == "KEYWORD" and token[1] in {"true", "false"}:
            return NodoBooleano(self.coincidir("KEYWORD"))
        if token[0] == "IDENTIFIER":
            identificador = self.coincidir("IDENTIFIER")
            if self._valor_actual("("):
                self.coincidir("DELIMITER", "(")
                argumentos = self.argumentos()
                self.coincidir("DELIMITER", ")")
                return NodoLlamadaFuncion(identificador[1], argumentos)
            return NodoIdentificador(identificador)
        if token[0] == "DELIMITER" and token[1] == "(":
            self.coincidir("DELIMITER", "(")
            expresion = self.expresion()
            self.coincidir("DELIMITER", ")")
            return expresion
        raise ErrorSintactico(f"Expresion no valida: {token}")

    def argumentos(self):
        argumentos = []
        if self._valor_actual(")"):
            return argumentos
        argumentos.append(self.expresion())
        while self._valor_actual(","):
            self.coincidir("DELIMITER", ",")
            argumentos.append(self.expresion())
        return argumentos

    def _valor_actual(self, valor):
        token = self.obtener_token_actual()
        return token is not None and token[1] == valor


class ParserSentencia:
    # Parser de una sentencia de proceso, manteniendo el estilo del Parser de referencia.
    TIPOS = {"int", "float", "double", "bool", "string"}

    def __init__(self, tokens, node_id="", label="", codigo_original=""):
        self.tokens = tokens
        self.pos = 0
        self.node_id = node_id
        self.label = label
        self.codigo_original = codigo_original

    def obtener_token_actual(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def coincidir(self, tipo_esperado, valor_esperado=None):
        token_actual = self.obtener_token_actual()
        if token_actual and token_actual[0] == tipo_esperado:
            if valor_esperado is None or token_actual[1] == valor_esperado:
                self.pos += 1
                return token_actual
        esperado = f"{tipo_esperado} {valor_esperado}" if valor_esperado else tipo_esperado
        raise ErrorSintactico(f"Error sintactico: se esperaba {esperado}, pero se encontro: {token_actual}")

    def parsear(self):
        # Si el proceso no encaja como asignacion/incremento, se conserva como NodoProceso
        # para no romper diagramas parcialmente validos.
        if not self.tokens:
            return NodoProceso(self.codigo_original, node_id=self.node_id, label=self.label)
        if self._es_declaracion():
            nodo = self.asignacion(con_tipo=True)
        elif self._es_reasignacion():
            nodo = self.asignacion(con_tipo=False)
        elif self._es_incremento():
            nodo = self.incremento(1)
        elif self._es_decremento():
            nodo = self.incremento(-1)
        else:
            return NodoProceso(self.codigo_original, node_id=self.node_id, label=self.label)

        if self.obtener_token_actual() and self.obtener_token_actual()[1] == ";":
            self.coincidir("DELIMITER", ";")
        if self.obtener_token_actual() is not None:
            raise ErrorSintactico(f"Token inesperado al final de sentencia: {self.obtener_token_actual()}")
        return nodo

    def asignacion(self, con_tipo):
        tipo = self.coincidir("KEYWORD") if con_tipo else None
        nombre = self.coincidir("IDENTIFIER")
        self.coincidir("OPERATOR", "=")
        fin = self.pos
        while fin < len(self.tokens) and self.tokens[fin][1] != ";":
            fin += 1
        expresion = ParserExpresion(self.tokens[self.pos:fin]).parsear()
        self.pos = fin
        return NodoAsignacion(tipo, nombre, expresion, node_id=self.node_id, label=self.label)

    def incremento(self, valor):
        nombre = self.coincidir("IDENTIFIER")
        operador = self.coincidir("OPERATOR")
        numero = NodoNumero(("NUMBER", str(abs(valor))))
        op = "+" if valor > 0 else "-"
        expresion = NodoOperacion(NodoIdentificador(nombre), ("OPERATOR", op), numero)
        if operador[1] not in {"++", "--"}:
            raise ErrorSintactico(f"Operador de incremento invalido: {operador}")
        return NodoAsignacion(None, nombre, expresion, node_id=self.node_id, label=self.label)

    def _es_declaracion(self):
        return (
            len(self.tokens) >= 4
            and self.tokens[0][0] == "KEYWORD"
            and self.tokens[0][1] in self.TIPOS
            and self.tokens[1][0] == "IDENTIFIER"
            and self.tokens[2] == ("OPERATOR", "=")
        )

    def _es_reasignacion(self):
        return (
            len(self.tokens) >= 3
            and self.tokens[0][0] == "IDENTIFIER"
            and self.tokens[1] == ("OPERATOR", "=")
        )

    def _es_incremento(self):
        return len(self.tokens) >= 2 and self.tokens[0][0] == "IDENTIFIER" and self.tokens[1] == ("OPERATOR", "++")

    def _es_decremento(self):
        return len(self.tokens) >= 2 and self.tokens[0][0] == "IDENTIFIER" and self.tokens[1] == ("OPERATOR", "--")


class ParserAST:
    def parsear(self, data):
        # Convierte el JSON de ReactFlow en un AST propio del compilador.
        flow = data.get("flow", {})
        nodes = flow.get("nodes", [])
        edges = flow.get("edges", [])

        self.node_map = self._crear_node_map(nodes)
        self.out_edges = self._crear_edges_salida(edges)
        self.in_edges = self._crear_edges_entrada(edges)
        self.end_ids = {node_id for node_id, node in self.node_map.items() if node.get("type") == "end"}

        start_nodes = [node for node in nodes if node.get("type") == "start"]
        if len(start_nodes) != 1:
            raise ErrorSintactico("El diagrama debe tener exactamente un nodo start.")

        start_id = start_nodes[0]["id"]
        instrucciones = self._recorrer_lineal(start_id, set(), detener_en=set())
        return NodoPrograma(
            instrucciones,
            language_target=data.get("languageTarget", "cpp"),
            node_id=start_id,
            label=start_nodes[0].get("data", {}).get("label", "Inicio"),
        )

    def parse(self, data):
        return self.parsear(data)

    def _crear_node_map(self, nodes):
        node_map = {}
        for node in nodes:
            node_id = node.get("id")
            if node_id in node_map:
                raise ErrorSintactico(f"Id de nodo duplicado: {node_id}.")
            node_map[node_id] = node
        return node_map

    def _crear_edges_salida(self, edges):
        out_edges = {}
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source not in self.node_map:
                raise ErrorSintactico(f"El edge '{edge.get('id')}' usa source inexistente: {source}.")
            if target not in self.node_map:
                raise ErrorSintactico(f"El edge '{edge.get('id')}' usa target inexistente: {target}.")
            out_edges.setdefault(source, []).append(edge)
        return out_edges

    def _crear_edges_entrada(self, edges):
        in_edges = {}
        for edge in edges:
            in_edges.setdefault(edge.get("target"), []).append(edge)
        return in_edges

    def _recorrer_lineal(self, node_id, visitados, detener_en):
        instrucciones = []
        actual_id = node_id

        while actual_id:
            if actual_id in detener_en:
                break
            if actual_id in visitados:
                break

            visitados.add(actual_id)
            node = self.node_map[actual_id]
            node_type = node.get("type")

            if node_type == "start":
                actual_id = self._siguiente_unico(actual_id, obligatorio=True)
                continue
            if node_type == "end":
                instrucciones.append(self._crear_nodo(node))
                break
            if node_type in {"condition", "decision"}:
                estructura, siguiente_id = self._crear_estructura_control(node, visitados, instrucciones)
                instrucciones.append(estructura)
                actual_id = siguiente_id
                continue

            instrucciones.append(self._crear_nodo(node))
            actual_id = self._siguiente_unico(actual_id, obligatorio=True)

        return instrucciones

    def _crear_estructura_control(self, node, visitados, instrucciones_previas):
        # Una condition puede representar:
        # - if/else si ambas ramas siguen hacia un punto de union.
        # - while si una rama vuelve a la misma condicion.
        # - for si ademas hay init antes e incremento al final del cuerpo.
        node_id = node["id"]
        edges = self.out_edges.get(node_id, [])
        true_edge = self._edge_por_handle(edges, "true") or self._edge_por_label(edges, "si") or self._edge_por_indice(edges, 0)
        false_edge = self._edge_por_handle(edges, "false") or self._edge_por_label(edges, "no") or self._edge_por_indice(edges, 1)
        if not true_edge or not false_edge:
            raise ErrorSintactico(f"La condicion '{node_id}' debe tener ramas true y false.")

        data = node.get("data") or {}
        condicion = self._parsear_expresion(self._texto_condicion(data))

        true_target = true_edge["target"]
        false_target = false_edge["target"]
        true_returns = self._alcanza(true_target, node_id, set())
        false_returns = self._alcanza(false_target, node_id, set())

        if true_returns and not false_returns:
            cuerpo = self._recorrer_lineal(true_target, set(visitados), {node_id})
            nodo_for = self._intentar_crear_for(instrucciones_previas, condicion, cuerpo, node)
            if nodo_for:
                return nodo_for, false_target
            return NodoWhile(condicion, cuerpo, node_id=node_id, label=data.get("label", "")), false_target
        if false_returns and not true_returns:
            cuerpo = self._recorrer_lineal(false_target, set(visitados), {node_id})
            nodo_for = self._intentar_crear_for(instrucciones_previas, NodoUnario(("OPERATOR", "!"), condicion), cuerpo, node)
            if nodo_for:
                return nodo_for, true_target
            condicion_invertida = NodoUnario(("OPERATOR", "!"), condicion)
            return NodoWhile(condicion_invertida, cuerpo, node_id=node_id, label=data.get("label", "")), true_target

        join_id = self._primer_join(true_target, false_target)
        return NodoIf(
            condicion,
            self._recorrer_lineal(true_target, set(visitados), {join_id}),
            self._recorrer_lineal(false_target, set(visitados), {join_id}),
            node_id=node_id,
            label=data.get("label", ""),
        ), join_id

    def _crear_nodo(self, node):
        # Normaliza cada figura del diagrama a un nodo AST compilable.
        # Soporta data estructurado y texto directo escrito dentro de la figura.
        data = node.get("data") or {}
        node_id = node["id"]
        node_type = node.get("type")
        label = data.get("label", "")
        texto_figura = self._texto_figura(data)

        if node_type == "input":
            variable = data.get("variable", data.get("name"))
            data_type = data.get("dataType", data.get("type", "int"))
            if not variable:
                variable = self._parsear_texto_entrada(texto_figura)
            return NodoEntrada(
                ("KEYWORD", data_type),
                ("IDENTIFIER", variable),
                node_id=node_id,
                label=label,
            )
        if node_type == "output":
            expresion = self._texto(data, "expression", "value", "code")
            if not expresion:
                expresion = self._parsear_texto_salida(texto_figura)
            return NodoPrint(self._parsear_argumentos_salida(expresion), node_id=node_id, label=label)
        if node_type == "process":
            codigo = self._texto(data, "expression", "code") or texto_figura
            return self._parsear_sentencia(codigo, node_id, label)
        if node_type == "end":
            return NodoFin(node_id=node_id, label=label)

        raise ErrorSintactico(f"Tipo de nodo no soportado: {node_type}.")

    def _parsear_expresion(self, expresion):
        return ParserExpresion(identificar_tokens(expresion or "")).parsear()

    def _parsear_expresion_o_cadena(self, expresion):
        # En salidas, si "Mostrar Edad menor a 18" no es expresion valida,
        # se trata como cadena literal para printf.
        try:
            return self._parsear_expresion(expresion)
        except Exception:
            texto = str(expresion).strip().replace("\\", "\\\\").replace('"', '\\"')
            return NodoCadena(("STRING", f'"{texto}"'))

    def _parsear_argumentos_salida(self, expresion):
        partes = self._separar_por_comas(expresion)
        return [self._parsear_expresion_o_cadena(parte) for parte in partes] or [NodoCadena(("STRING", '""'))]

    def _separar_por_comas(self, texto):
        partes = []
        actual = []
        en_cadena = False
        escape = False

        for caracter in str(texto or ""):
            if escape:
                actual.append(caracter)
                escape = False
                continue
            if caracter == "\\":
                actual.append(caracter)
                escape = True
                continue
            if caracter == '"':
                actual.append(caracter)
                en_cadena = not en_cadena
                continue
            if caracter == "," and not en_cadena:
                parte = "".join(actual).strip()
                if parte:
                    partes.append(parte)
                actual = []
                continue
            actual.append(caracter)

        parte = "".join(actual).strip()
        if parte:
            partes.append(parte)
        return partes

    def _parsear_sentencia(self, codigo, node_id, label):
        tokens = identificar_tokens(codigo or "")
        return ParserSentencia(tokens, node_id=node_id, label=label, codigo_original=codigo or "").parsear()

    def _texto(self, data, *keys):
        for key in keys:
            valor = data.get(key)
            if valor is not None and str(valor).strip():
                return str(valor)
        return ""

    def _texto_condicion(self, data):
        texto = self._texto(data, "expression", "condition", "code")
        if texto:
            return texto
        label = self._texto_figura(data)
        return label.strip().lstrip("¿?").rstrip("?") if label else ""

    def _texto_figura(self, data):
        # Prioridad de campos donde el frontend puede guardar el texto visible.
        return self._texto(data, "text", "label", "value", "code", "expression")

    def _parsear_texto_entrada(self, texto):
        # Convierte "Leer edad" en variable "edad".
        partes = (texto or "").strip().split()
        if len(partes) >= 2 and partes[0].lower() in {"leer", "input", "ingresar"}:
            return partes[1]
        return texto.strip()

    def _parsear_texto_salida(self, texto):
        # Convierte "Mostrar x" en expresion x; si no tiene prefijo, se imprime como texto.
        texto = (texto or "").strip()
        if not texto:
            return '""'
        for prefijo in ("Mostrar ", "mostrar ", "Print ", "print ", "Imprimir ", "imprimir "):
            if texto.startswith(prefijo):
                return texto[len(prefijo):].strip() or '""'
        return f'"{texto}"'

    def _intentar_crear_for(self, instrucciones_previas, condicion, cuerpo, node):
        # Heuristica conservadora para for:
        # ultima instruccion antes de la condicion debe ser declaracion,
        # y ultima instruccion del cuerpo debe modificar la misma variable.
        if not instrucciones_previas or not cuerpo:
            return None
        init = instrucciones_previas[-1]
        incremento = cuerpo[-1]
        if not isinstance(init, NodoAsignacion) or init.tipo is None:
            return None
        if not isinstance(incremento, NodoAsignacion):
            return None
        if init.nombre[1] != incremento.nombre[1]:
            return None

        instrucciones_previas.pop()
        data = node.get("data") or {}
        return NodoFor(
            init,
            condicion,
            incremento,
            cuerpo[:-1],
            node_id=node["id"],
            label=data.get("label", ""),
        )

    def _siguiente_unico(self, node_id, obligatorio):
        edges = self.out_edges.get(node_id, [])
        if not edges:
            if obligatorio:
                raise ErrorSintactico(f"El nodo '{node_id}' no tiene conexion de salida.")
            return None
        if len(edges) > 1:
            raise ErrorSintactico(f"El nodo '{node_id}' tiene multiples salidas; use un nodo condition.")
        return edges[0].get("target")

    def _edge_por_handle(self, edges, handle):
        for edge in edges:
            if edge.get("sourceHandle") == handle:
                return edge
        return None

    def _edge_por_label(self, edges, label):
        label = label.lower()
        opciones = {"si": {"si", "sí", "true", "verdadero"}, "no": {"no", "false", "falso"}}
        for edge in edges:
            edge_label = str((edge.get("data") or {}).get("label", "")).strip().lower()
            if edge_label in opciones[label]:
                return edge
        return None

    def _edge_por_indice(self, edges, index):
        if len(edges) > index:
            return edges[index]
        return None

    def _primer_join(self, true_id, false_id):
        true_reach = self._alcanzables_lineales(true_id)
        actual_id = false_id
        visitados = set()

        while actual_id and actual_id not in visitados:
            if actual_id in true_reach:
                return actual_id
            visitados.add(actual_id)
            if actual_id in self.end_ids:
                break
            actual_id = self._siguiente_lineal_para_join(actual_id)

        common_ends = true_reach.intersection(self.end_ids)
        if common_ends:
            return next(iter(common_ends))
        raise ErrorSintactico("Las ramas true y false de una condicion deben volver a un mismo nodo.")

    def _alcanzables_lineales(self, node_id):
        alcanzables = []
        actual_id = node_id
        visitados = set()
        while actual_id and actual_id not in visitados:
            alcanzables.append(actual_id)
            visitados.add(actual_id)
            if actual_id in self.end_ids:
                break
            actual_id = self._siguiente_lineal_para_join(actual_id)
        return set(alcanzables)

    def _siguiente_lineal_para_join(self, node_id):
        edges = self.out_edges.get(node_id, [])
        if not edges:
            return None
        if len(edges) == 1:
            return edges[0].get("target")
        return None

    def _alcanza(self, origen, destino, visitados):
        if origen == destino:
            return True
        if origen in visitados:
            return False
        visitados.add(origen)
        for edge in self.out_edges.get(origen, []):
            if self._alcanza(edge.get("target"), destino, visitados):
                return True
        return False
