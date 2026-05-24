# Analizador semantico compatible con el AST generado desde el diagrama.

from sintactico_ast import (
    NodoAsignacion,
    NodoBooleano,
    NodoCadena,
    NodoEntrada,
    NodoFin,
    NodoFor,
    NodoIdentificador,
    NodoIf,
    NodoLlamadaFuncion,
    NodoNumero,
    NodoOperacion,
    NodoPrint,
    NodoProceso,
    NodoPrograma,
    NodoUnario,
    NodoWhile,
)


class ErrorSemantico(Exception):
    pass


class TablaSimbolos:
    TIPOS_VALIDOS = {"int", "float", "double", "bool", "string"}

    def __init__(self):
        self.ambitos = [{}]
        self.declaradas = {}

    def entrar_ambito(self):
        self.ambitos.append({})

    def salir_ambito(self):
        if len(self.ambitos) == 1:
            raise ErrorSemantico("No se puede salir del ambito global.")
        self.ambitos.pop()

    def declarar_variable(self, nombre, tipo, ubicacion=""):
        self._validar_nombre(nombre, ubicacion)
        self._validar_tipo(tipo, ubicacion)
        ambito = self.ambitos[-1]
        if nombre in ambito:
            sufijo = self._sufijo_ubicacion(ubicacion)
            raise ErrorSemantico(
                f"La variable '{nombre}' ya existe{sufijo}. Usa otro nombre o no la declares dos veces."
            )
        ambito[nombre] = tipo
        self.declaradas[nombre] = tipo

    def asignar_variable(self, nombre, tipo_expr, ubicacion=""):
        tipo_actual = self.obtener_tipo_variable(nombre, ubicacion)
        if not SistemaTipos.es_asignable(tipo_actual, tipo_expr):
            raise ErrorSemantico(
                f"No se puede guardar un valor de tipo {tipo_expr} en la variable '{nombre}', porque esa variable es de tipo {tipo_actual}."
            )

    def obtener_tipo_variable(self, nombre, ubicacion=""):
        for ambito in reversed(self.ambitos):
            if nombre in ambito:
                return ambito[nombre]
        sufijo = self._sufijo_ubicacion(ubicacion)
        raise ErrorSemantico(
            f"La variable '{nombre}' no existe{sufijo}. Antes de usarla debes crearla con una figura de entrada o con un proceso, por ejemplo: int {nombre} = 0."
        )

    def serializar(self):
        return dict(self.declaradas)

    def _validar_tipo(self, tipo, ubicacion=""):
        if tipo not in self.TIPOS_VALIDOS:
            sufijo = self._sufijo_ubicacion(ubicacion)
            raise ErrorSemantico(
                f"El tipo de dato '{tipo}' no esta permitido{sufijo}. Usa int, float, double, bool o string."
            )

    def _validar_nombre(self, nombre, ubicacion=""):
        if not nombre or not nombre.replace("_", "a").isalnum() or nombre[0].isdigit():
            sufijo = self._sufijo_ubicacion(ubicacion)
            raise ErrorSemantico(
                f"El nombre de variable '{nombre}' no es valido{sufijo}. Escribe solo el nombre, por ejemplo: edad. No escribas 'Leer edad'."
            )

    def _sufijo_ubicacion(self, ubicacion):
        return f" en figura '{ubicacion}'" if ubicacion else ""


class SistemaTipos:
    NUMERICOS = {"int", "float", "double"}

    @staticmethod
    def es_numerico(tipo):
        return tipo in SistemaTipos.NUMERICOS

    @staticmethod
    def es_asignable(tipo_destino, tipo_origen):
        if tipo_destino == tipo_origen:
            return True
        if tipo_destino in {"float", "double"} and tipo_origen in {"int", "float"}:
            return True
        if tipo_destino == "bool" and tipo_origen in {"int", "bool"}:
            return True
        return False

    @staticmethod
    def tipo_resultante(tipo_izq, tipo_der, operador):
        if operador in {"<", ">", "<=", ">=", "==", "!=", "&&", "||"}:
            return "bool"
        if tipo_izq == "string" or tipo_der == "string":
            if operador == "+" and tipo_izq == tipo_der == "string":
                return "string"
            raise ErrorSemantico(f"Operacion no valida con string: {tipo_izq} {operador} {tipo_der}.")
        if not SistemaTipos.es_numerico(tipo_izq) or not SistemaTipos.es_numerico(tipo_der):
            raise ErrorSemantico(f"Operacion no valida: {tipo_izq} {operador} {tipo_der}.")
        if "double" in {tipo_izq, tipo_der}:
            return "double"
        if "float" in {tipo_izq, tipo_der}:
            return "float"
        return "int"

    @staticmethod
    def validar_condicion(tipo, contexto):
        if tipo not in {"bool", "int"}:
            raise ErrorSemantico(f"La condicion de {contexto} debe ser bool o int, recibio {tipo}.")


class AnalizadorSemantico:
    def __init__(self):
        self.tabla_simbolos = TablaSimbolos()
        self.warnings = []
        self.contexto_figura = ""

    def analizar(self, nodo):
        metodo = f"visitar_{type(nodo).__name__}"
        if not hasattr(self, metodo):
            raise ErrorSemantico(f"No se ha implementado analisis semantico para {type(nodo).__name__}.")

        contexto_anterior = self.contexto_figura
        nuevo_contexto = self._nombre_figura(nodo)
        if nuevo_contexto:
            self.contexto_figura = nuevo_contexto

        try:
            return getattr(self, metodo)(nodo)
        finally:
            self.contexto_figura = contexto_anterior

    def visitar_NodoPrograma(self, nodo):
        for instruccion in nodo.instrucciones:
            self.analizar(instruccion)
        return {
            "simbolos": self.tabla_simbolos.serializar(),
            "warnings": self.warnings,
        }

    def visitar_NodoEntrada(self, nodo):
        self.tabla_simbolos.declarar_variable(nodo.nombre[1], nodo.tipo[1], self.contexto_figura)
        return nodo.tipo[1]

    def visitar_NodoAsignacion(self, nodo):
        tipo_expr = self.analizar(nodo.expresion)
        nombre = nodo.nombre[1]

        if nodo.tipo is not None:
            tipo_declarado = nodo.tipo[1]
            self.tabla_simbolos.declarar_variable(nombre, tipo_declarado, self.contexto_figura)
            if not SistemaTipos.es_asignable(tipo_declarado, tipo_expr):
                raise ErrorSemantico(
                    f"No se puede iniciar la variable '{nombre}' con un valor de tipo {tipo_expr}, porque fue declarada como {tipo_declarado}."
                )
            return tipo_declarado

        self.tabla_simbolos.asignar_variable(nombre, tipo_expr, self.contexto_figura)
        return self.tabla_simbolos.obtener_tipo_variable(nombre, self.contexto_figura)

    def visitar_NodoProceso(self, nodo):
        self.warnings.append(
            f"No se valido semanticamente el proceso '{nodo.expresion}' en figura '{self.contexto_figura}'."
        )
        return "void"

    def visitar_NodoPrint(self, nodo):
        for argumento in nodo.argumentos:
            self.analizar(argumento)
        return "void"

    def visitar_NodoIf(self, nodo):
        tipo_condicion = self.analizar(nodo.condicion)
        SistemaTipos.validar_condicion(tipo_condicion, "if")

        self.tabla_simbolos.entrar_ambito()
        for instruccion in nodo.cuerpo:
            self.analizar(instruccion)
        self.tabla_simbolos.salir_ambito()

        self.tabla_simbolos.entrar_ambito()
        for instruccion in nodo.sino:
            self.analizar(instruccion)
        self.tabla_simbolos.salir_ambito()
        return "void"

    def visitar_NodoWhile(self, nodo):
        tipo_condicion = self.analizar(nodo.condicion)
        SistemaTipos.validar_condicion(tipo_condicion, "while")

        self.tabla_simbolos.entrar_ambito()
        for instruccion in nodo.cuerpo:
            self.analizar(instruccion)
        self.tabla_simbolos.salir_ambito()
        return "void"

    def visitar_NodoFor(self, nodo):
        self.analizar(nodo.init)

        tipo_condicion = self.analizar(nodo.condicion)
        SistemaTipos.validar_condicion(tipo_condicion, "for")

        self.tabla_simbolos.entrar_ambito()
        for instruccion in nodo.cuerpo:
            self.analizar(instruccion)
        self.tabla_simbolos.salir_ambito()

        self.analizar(nodo.incremento)
        return "void"

    def visitar_NodoOperacion(self, nodo):
        tipo_izq = self.analizar(nodo.izquierda)
        tipo_der = self.analizar(nodo.derecha)
        operador = nodo.operador[1]

        if operador in {"&&", "||"}:
            SistemaTipos.validar_condicion(tipo_izq, "operador logico")
            SistemaTipos.validar_condicion(tipo_der, "operador logico")
            return "bool"

        if operador in {"==", "!="}:
            if tipo_izq != tipo_der and not (
                SistemaTipos.es_numerico(tipo_izq) and SistemaTipos.es_numerico(tipo_der)
            ):
                raise ErrorSemantico(
                    f"La comparacion no es valida: estas comparando {tipo_izq} con {tipo_der}."
                )
            return "bool"

        if operador in {"<", ">", "<=", ">="}:
            if not SistemaTipos.es_numerico(tipo_izq) or not SistemaTipos.es_numerico(tipo_der):
                raise ErrorSemantico(
                    f"La comparacion usa valores que no son numericos: {tipo_izq} {operador} {tipo_der}."
                )
            return "bool"

        return SistemaTipos.tipo_resultante(tipo_izq, tipo_der, operador)

    def visitar_NodoUnario(self, nodo):
        tipo = self.analizar(nodo.expresion)
        operador = nodo.operador[1]
        if operador == "!":
            SistemaTipos.validar_condicion(tipo, "operador !")
            return "bool"
        if operador == "-":
            if not SistemaTipos.es_numerico(tipo):
                raise ErrorSemantico(f"El operador - requiere tipo numerico, recibio {tipo}.")
            return tipo
        raise ErrorSemantico(f"Operador unario no soportado: {operador}.")

    def visitar_NodoIdentificador(self, nodo):
        return self.tabla_simbolos.obtener_tipo_variable(nodo.nombre[1], self.contexto_figura)

    def visitar_NodoNumero(self, nodo):
        return "float" if "." in str(nodo.valor[1]) else "int"

    def visitar_NodoCadena(self, nodo):
        return "string"

    def visitar_NodoBooleano(self, nodo):
        return "bool"

    def visitar_NodoLlamadaFuncion(self, nodo):
        self.warnings.append(
            f"No se pudo validar la llamada a funcion '{nodo.nombre_funcion}'; se asumio retorno int."
        )
        for argumento in nodo.argumentos:
            self.analizar(argumento)
        return "int"

    def visitar_NodoFin(self, nodo):
        return "void"

    def _nombre_figura(self, nodo):
        label = getattr(nodo, "label", "")
        if label:
            return label
        if isinstance(nodo, NodoEntrada):
            return f"Leer {nodo.nombre[1]}"
        if isinstance(nodo, NodoAsignacion):
            return nodo.traducirCpp().splitlines()[0].rstrip(";")
        if isinstance(nodo, NodoPrint):
            return "Salida"
        if isinstance(nodo, NodoIf):
            return nodo.condicion.traducirCpp()
        if isinstance(nodo, NodoWhile):
            return nodo.condicion.traducirCpp()
        if isinstance(nodo, NodoFor):
            return "For"
        return ""


def analizar_semantica(programa):
    return AnalizadorSemantico().analizar(programa)
