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
        return "%g" if "." in nodo.valor[1] else "%d"
    if isinstance(nodo, NodoIdentificador):
        tipo = NodoAST.tipos_variables.get(nodo.nombre[1], "int")
        return "%s" if tipo == "string" else "%g" if tipo in {"float", "double"} else "%d"
    return "%d"

ASM_STRING_SIZE = 256

ASM_BUILTINS = {
    "len", "strlen", "length",
    "abs", "sqrt", "sin", "cos",
    "int", "float", "double",
    "max", "min",
    "concat",
}


def _literal_python(cadena_token):
    import ast as _ast
    try:
        return str(_ast.literal_eval(cadena_token))
    except Exception:
        texto = str(cadena_token)
        if len(texto) >= 2 and texto[0] == '"' and texto[-1] == '"':
            return texto[1:-1]
        return texto


def _db_string(cadena_token):
    texto = _literal_python(cadena_token)
    partes = []
    actual = []

    for ch in texto:
        codigo = ord(ch)
        if ch == '"':
            actual.append('\\"')
        elif ch == "\\":
            actual.append('\\\\')
        elif 32 <= codigo <= 126:
            actual.append(ch)
        else:
            if actual:
                partes.append('"' + ''.join(actual) + '"')
                actual = []
            partes.append(str(codigo))

    if actual:
        partes.append('"' + ''.join(actual) + '"')

    partes.append("0")
    return ", ".join(partes)


def _es_float_literal(texto):
    texto = str(texto).lower()
    return "." in texto or "e" in texto


def _es_tipo_float(tipo):
    return tipo in {"float", "double"}


def _tam_tipo_float(tipo):
    return "dword" if tipo == "float" else "qword"


def _tipo_variable(nombre):
    return NodoAST.tipos_variables.get(nombre, "int")


def _tipo_expr(nodo):
    if isinstance(nodo, NodoCadena):
        return "string"

    if isinstance(nodo, NodoBooleano):
        return "bool"

    if isinstance(nodo, NodoNumero):
        return "double" if _es_float_literal(nodo.valor[1]) else "int"

    if isinstance(nodo, NodoIdentificador):
        return _tipo_variable(nodo.nombre[1])

    if isinstance(nodo, NodoUnario):
        if nodo.operador[1] == "!":
            return "bool"
        return _tipo_expr(nodo.expresion)

    if isinstance(nodo, NodoOperacion):
        op = nodo.operador[1]

        if op in {">", "<", ">=", "<=", "==", "!=", "&&", "||"}:
            return "bool"

        ti = _tipo_expr(nodo.izquierda)
        td = _tipo_expr(nodo.derecha)

        if ti == "string" or td == "string":
            return "string" if op == "+" else "bool"

        if ti == "double" or td == "double":
            return "double"

        if ti == "float" or td == "float":
            return "float"

        return "int"

    if isinstance(nodo, NodoLlamadaFuncion):
        nombre = nodo.nombre_funcion

        if nombre in {"len", "strlen", "length", "int"}:
            return "int"

        if nombre in {"sqrt", "sin", "cos", "float", "double"}:
            return "double"

        if nombre == "concat":
            return "string"

        if nombre == "abs" and nodo.argumentos:
            return _tipo_expr(nodo.argumentos[0])
        
        if nombre in {"max", "min"} and len(nodo.argumentos) >= 2:
            tipo_a = _tipo_expr(nodo.argumentos[0])
            tipo_b = _tipo_expr(nodo.argumentos[1])

            if tipo_a == "double" or tipo_b == "double":
                return "double"

            if tipo_a == "float" or tipo_b == "float":
                return "float"

            return "int"

    return "int"


def _gen_float(nodo):
    metodo = getattr(nodo, "generarCodigoFloat", None)
    if metodo:
        return metodo()

    return "\n".join([
        nodo.generarCodigo(),
        "    mov [tmp_int], eax",
        "    fild dword [tmp_int]",
    ])


def _gen_bool(nodo):
    tipo = _tipo_expr(nodo)

    if tipo == "string":
        return "\n".join([
            nodo.generarCodigo(),
            "    mov esi, eax",
            "    call funcion_contar_texto",
            "    cmp eax, 0",
            "    setne al",
            "    movzx eax, al",
        ])

    if tipo in {"float", "double"}:
        return "\n".join([
            _gen_float(nodo),
            "    ftst",
            "    fstsw ax",
            "    sahf",
            "    fstp st0",
            "    setne al",
            "    movzx eax, al",
        ])

    return nodo.generarCodigo()


def _collect_expr_calls(nodo, llamadas):
    if isinstance(nodo, NodoLlamadaFuncion):
        if nodo.nombre_funcion not in ASM_BUILTINS:
            llamadas.add(nodo.nombre_funcion)

        for arg in nodo.argumentos:
            _collect_expr_calls(arg, llamadas)

    elif isinstance(nodo, NodoOperacion):
        _collect_expr_calls(nodo.izquierda, llamadas)
        _collect_expr_calls(nodo.derecha, llamadas)

    elif isinstance(nodo, NodoUnario):
        _collect_expr_calls(nodo.expresion, llamadas)


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
        NodoAST.contador_etiquetas = 0
        self.variables = self._recolectar_variables(self.instrucciones)
        NodoAST.tipos_variables = {nombre: tipo for tipo, nombre in self.variables}

        self.cadenas = {}
        self.constantes_float = {}
        self.llamadas_externas = set()

        self._recolectar_constantes(
            self.instrucciones,
            self.cadenas,
            self.constantes_float
        )

        self._recolectar_llamadas(
            self.instrucciones,
            self.llamadas_externas
        )

        data = [
            "section .data",
            "    newline: db 10",
            "    space_chr: db 32",
            "    const_10: dq 10.0",
            "    const_round: dq 0.0000005",
            "    fpu_cw_trunc: dw 0",
        ]

        for etiqueta, valor in self.cadenas.items():
            data.append(f"    {etiqueta}: db {_db_string(valor)}")

        for etiqueta, valor in self.constantes_float.items():
            data.append(f"    {etiqueta}: dq {valor}")

        bss = [
            "section .bss",
            "    print_buffer: resb 128",
            "    input_buffer: resb 256",
            "    string_temp: resb 256",
            "    string_temp2: resb 256",
            "    tmp_int: resd 1",
            "    tmp_divisor: resd 1",
            "    fpu_cw: resw 1",
        ]

        for tipo, nombre in self.variables:
            if tipo in ("int", "bool"):
                bss.append(f"    {nombre}: resd 1")
            elif tipo == "float":
                bss.append(f"    {nombre}: resd 1")
            elif tipo == "double":
                bss.append(f"    {nombre}: resq 1")
            elif tipo == "string":
                bss.append(f"    {nombre}: resb {ASM_STRING_SIZE}")
            else:
                bss.append(f"    {nombre}: resd 1")

        text_header = [
            "section .text",
            "global _start",
        ]

        for nombre in sorted(self.llamadas_externas):
            text_header.append(f"extern {nombre}")

        text_header.append("_start:")

        codigo = text_header

        codigo.extend(
            i.generarCodigo()
            for i in self.instrucciones
            if not isinstance(i, NodoFin)
        )

        codigo.extend(self._runtime_asm())

        return "\n".join(data + [""] + bss + [""] + codigo)

    def _obtener_etiqueta_cadena(self, valor, cadenas):
        for etiqueta, existente in cadenas.items():
            if existente == valor:
                return etiqueta

        etiqueta = f"str_{len(cadenas)}"
        cadenas[etiqueta] = valor
        return etiqueta


    def _obtener_etiqueta_float(self, valor, constantes_float):
        for etiqueta, existente in constantes_float.items():
            if existente == valor:
                return etiqueta

        etiqueta = f"flt_{len(constantes_float)}"
        constantes_float[etiqueta] = valor
        return etiqueta


    def _recolectar_constantes(self, instrucciones, cadenas, constantes_float):
        for inst in instrucciones:
            if isinstance(inst, NodoEntrada) and inst.prompt:
                self._recolectar_constantes_expr(inst.prompt, cadenas, constantes_float)

            if isinstance(inst, NodoPrint):
                for arg in inst.argumentos:
                    self._recolectar_constantes_expr(arg, cadenas, constantes_float)

            elif isinstance(inst, NodoIf):
                self._recolectar_constantes_expr(inst.condicion, cadenas, constantes_float)
                self._recolectar_constantes(inst.cuerpo, cadenas, constantes_float)
                self._recolectar_constantes(inst.sino, cadenas, constantes_float)

            elif isinstance(inst, NodoWhile):
                self._recolectar_constantes_expr(inst.condicion, cadenas, constantes_float)
                self._recolectar_constantes(inst.cuerpo, cadenas, constantes_float)

            elif isinstance(inst, NodoFor):
                self._recolectar_constantes([inst.init], cadenas, constantes_float)
                self._recolectar_constantes_expr(inst.condicion, cadenas, constantes_float)
                self._recolectar_constantes([inst.incremento], cadenas, constantes_float)
                self._recolectar_constantes(inst.cuerpo, cadenas, constantes_float)

            elif isinstance(inst, NodoAsignacion):
                self._recolectar_constantes_expr(inst.expresion, cadenas, constantes_float)

            elif isinstance(inst, NodoExpresionSentencia):
                self._recolectar_constantes_expr(inst.expresion, cadenas, constantes_float)

    def _recolectar_constantes_expr(self, nodo, cadenas, constantes_float):
        if isinstance(nodo, NodoCadena):
            nodo.etiqueta = self._obtener_etiqueta_cadena(nodo.valor[1], cadenas)

        elif isinstance(nodo, NodoNumero):
            if _es_float_literal(nodo.valor[1]):
                nodo.etiqueta_float = self._obtener_etiqueta_float(
                    nodo.valor[1],
                    constantes_float
                )

        elif isinstance(nodo, NodoOperacion):
            self._recolectar_constantes_expr(nodo.izquierda, cadenas, constantes_float)
            self._recolectar_constantes_expr(nodo.derecha, cadenas, constantes_float)

        elif isinstance(nodo, NodoUnario):
            self._recolectar_constantes_expr(nodo.expresion, cadenas, constantes_float)

        elif isinstance(nodo, NodoLlamadaFuncion):
            for arg in nodo.argumentos:
                self._recolectar_constantes_expr(arg, cadenas, constantes_float)

    def _recolectar_cadenas(self, instrucciones, cadenas):
        self._recolectar_constantes(instrucciones, cadenas, {})

    def _recolectar_llamadas(self, instrucciones, llamadas):
        for inst in instrucciones:
            if isinstance(inst, NodoPrint):
                for arg in inst.argumentos:
                    _collect_expr_calls(arg, llamadas)

            elif isinstance(inst, NodoAsignacion):
                _collect_expr_calls(inst.expresion, llamadas)

            elif isinstance(inst, NodoExpresionSentencia):
                _collect_expr_calls(inst.expresion, llamadas)

            elif isinstance(inst, NodoIf):
                _collect_expr_calls(inst.condicion, llamadas)
                self._recolectar_llamadas(inst.cuerpo, llamadas)
                self._recolectar_llamadas(inst.sino, llamadas)

            elif isinstance(inst, NodoWhile):
                _collect_expr_calls(inst.condicion, llamadas)
                self._recolectar_llamadas(inst.cuerpo, llamadas)

            elif isinstance(inst, NodoFor):
                self._recolectar_llamadas([inst.init], llamadas)
                _collect_expr_calls(inst.condicion, llamadas)
                self._recolectar_llamadas([inst.incremento], llamadas)
                self._recolectar_llamadas(inst.cuerpo, llamadas)

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
                if instruccion.tipo[1]:
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

    def _runtime_asm(self):
        return [
            "",
            "    ; terminar programa",
            "    mov eax, 1",
            "    mov ebx, 0",
            "    int 0x80",

            "",
            "; convertir entero a texto",
            "funcion_entero_a_texto:",
            "    push ebx",
            "    push ecx",
            "    push edx",
            "    push edi",
            "    mov edi, esi",
            "    xor ecx, ecx",
            "    mov ebx, 10",
            "    cmp eax, 0",
            "    jne .entero_revisar_signo",
            "    mov byte [esi], '0'",
            "    inc esi",
            "    mov eax, 1",
            "    jmp .entero_salir",
            ".entero_revisar_signo:",
            "    cmp eax, 0",
            "    jge .entero_ciclo",
            "    mov byte [esi], '-'",
            "    inc esi",
            "    neg eax",
            ".entero_ciclo:",
            "    xor edx, edx",
            "    div ebx",
            "    push edx",
            "    inc ecx",
            "    cmp eax, 0",
            "    jne .entero_ciclo",
            ".entero_sacar_digito:",
            "    pop edx",
            "    add dl, '0'",
            "    mov [esi], dl",
            "    inc esi",
            "    loop .entero_sacar_digito",
            "    mov eax, esi",
            "    sub eax, edi",
            ".entero_salir:",
            "    pop edi",
            "    pop edx",
            "    pop ecx",
            "    pop ebx",
            "    ret",

            "",
            "; leer una linea del teclado",
            "funcion_leer_linea:",
            "    push ebx",
            "    push ecx",
            "    push edx",
            "    push edi",
            "    push esi",
            "    xor esi, esi",
            "    cmp edx, 1",
            "    jbe .leer_linea_vacia",
            "    dec edx",
            ".leer_linea_ciclo:",
            "    cmp esi, edx",
            "    jge .leer_linea_fin",
            "    mov eax, 3",
            "    mov ebx, 0",
            "    lea ecx, [edi + esi]",
            "    push edx",
            "    mov edx, 1",
            "    int 0x80",
            "    pop edx",
            "    cmp eax, 0",
            "    jle .leer_linea_fin",
            "    cmp byte [edi + esi], 10",
            "    je .leer_linea_fin",
            "    inc esi",
            "    jmp .leer_linea_ciclo",
            ".leer_linea_fin:",
            "    mov byte [edi + esi], 0",
            "    mov eax, esi",
            "    jmp .leer_linea_salir",
            ".leer_linea_vacia:",
            "    mov byte [edi], 0",
            "    xor eax, eax",
            ".leer_linea_salir:",
            "    pop esi",
            "    pop edi",
            "    pop edx",
            "    pop ecx",
            "    pop ebx",
            "    ret",

            "",
            "; convertir texto a entero",
            "funcion_texto_a_entero:",
            "    push ebx",
            "    push ecx",
            "    push edx",
            "    xor eax, eax",
            "    xor ecx, ecx",
            ".texto_entero_saltar:",
            "    mov bl, [esi]",
            "    cmp bl, ' '",
            "    je .texto_entero_avanzar",
            "    cmp bl, 9",
            "    jne .texto_entero_signo",
            ".texto_entero_avanzar:",
            "    inc esi",
            "    jmp .texto_entero_saltar",
            ".texto_entero_signo:",
            "    xor edx, edx",
            "    cmp bl, '-'",
            "    jne .texto_entero_digito",
            "    mov edx, 1",
            "    inc esi",
            ".texto_entero_digito:",
            "    mov bl, [esi]",
            "    cmp bl, '0'",
            "    jb .texto_entero_fin",
            "    cmp bl, '9'",
            "    ja .texto_entero_fin",
            "    sub bl, '0'",
            "    imul eax, eax, 10",
            "    movzx ecx, bl",
            "    add eax, ecx",
            "    inc esi",
            "    jmp .texto_entero_digito",
            ".texto_entero_fin:",
            "    cmp edx, 0",
            "    je .texto_entero_salir",
            "    neg eax",
            ".texto_entero_salir:",
            "    pop edx",
            "    pop ecx",
            "    pop ebx",
            "    ret",

            "",
            "; convertir texto a double",
            "funcion_texto_a_double:",
            "    push eax",
            "    push ebx",
            "    push ecx",
            "    push edx",
            "    push edi",
            "    fldz",
            "    xor edi, edi",
            ".texto_double_saltar:",
            "    mov bl, [esi]",
            "    cmp bl, ' '",
            "    je .texto_double_avanzar",
            "    cmp bl, 9",
            "    jne .texto_double_signo",
            ".texto_double_avanzar:",
            "    inc esi",
            "    jmp .texto_double_saltar",
            ".texto_double_signo:",
            "    cmp bl, '-'",
            "    jne .texto_double_entero",
            "    mov edi, 1",
            "    inc esi",
            ".texto_double_entero:",
            "    mov bl, [esi]",
            "    cmp bl, '0'",
            "    jb .texto_double_revisar_decimal",
            "    cmp bl, '9'",
            "    ja .texto_double_revisar_decimal",
            "    fld qword [const_10]",
            "    fmulp st1, st0",
            "    movzx eax, bl",
            "    sub eax, '0'",
            "    mov [tmp_int], eax",
            "    fiadd dword [tmp_int]",
            "    inc esi",
            "    jmp .texto_double_entero",
            ".texto_double_revisar_decimal:",
            "    cmp bl, '.'",
            "    jne .texto_double_aplicar_signo",
            "    inc esi",
            "    mov dword [tmp_divisor], 10",
            ".texto_double_decimal:",
            "    mov bl, [esi]",
            "    cmp bl, '0'",
            "    jb .texto_double_aplicar_signo",
            "    cmp bl, '9'",
            "    ja .texto_double_aplicar_signo",
            "    movzx eax, bl",
            "    sub eax, '0'",
            "    mov [tmp_int], eax",
            "    fild dword [tmp_int]",
            "    fidiv dword [tmp_divisor]",
            "    faddp st1, st0",
            "    mov eax, [tmp_divisor]",
            "    imul eax, eax, 10",
            "    mov [tmp_divisor], eax",
            "    inc esi",
            "    jmp .texto_double_decimal",
            ".texto_double_aplicar_signo:",
            "    cmp edi, 0",
            "    je .texto_double_salir",
            "    fchs",
            ".texto_double_salir:",
            "    pop edi",
            "    pop edx",
            "    pop ecx",
            "    pop ebx",
            "    pop eax",
            "    ret",

            "",
            "; convertir double a texto",
            "funcion_double_a_texto:",
            "    push ebx",
            "    push ecx",
            "    push edx",
            "    push edi",
            "    fnstcw [fpu_cw]",
            "    mov ax, [fpu_cw]",
            "    and ax, 0xF3FF",
            "    or ax, 0x0C00",
            "    mov [fpu_cw_trunc], ax",
            "    fldcw [fpu_cw_trunc]",
            "    mov edi, esi",
            "    ftst",
            "    fstsw ax",
            "    sahf",
            "    jae .double_positivo",
            "    mov byte [esi], '-'",
            "    inc esi",
            "    fchs",
            ".double_positivo:",
            "    fadd qword [const_round]",
            "    fld st0",
            "    fistp dword [tmp_int]",
            "    mov eax, [tmp_int]",
            "    call funcion_entero_a_texto",
            "    fisub dword [tmp_int]",
            "    mov byte [esi], '.'",
            "    inc esi",
            "    mov ecx, 6",
            ".double_decimales:",
            "    fld qword [const_10]",
            "    fmulp st1, st0",
            "    fld st0",
            "    fistp dword [tmp_int]",
            "    mov eax, [tmp_int]",
            "    add al, '0'",
            "    mov [esi], al",
            "    inc esi",
            "    fisub dword [tmp_int]",
            "    loop .double_decimales",
            "    fstp st0",
            "    mov ebx, esi",
            "    dec ebx",
            ".double_quitar_ceros:",
            "    cmp byte [ebx], '0'",
            "    jne .double_quitar_punto",
            "    dec esi",
            "    dec ebx",
            "    jmp .double_quitar_ceros",
            ".double_quitar_punto:",
            "    cmp byte [ebx], '.'",
            "    jne .double_listo",
            "    dec esi",
            ".double_listo:",
            "    fldcw [fpu_cw]",
            "    mov eax, esi",
            "    sub eax, edi",
            "    pop edi",
            "    pop edx",
            "    pop ecx",
            "    pop ebx",
            "    ret",

            "",
            "; contar letras de un texto",
            "funcion_contar_texto:",
            "    push esi",
            "    xor eax, eax",
            ".contar_texto_ciclo:",
            "    cmp byte [esi], 0",
            "    je .contar_texto_fin",
            "    inc eax",
            "    inc esi",
            "    jmp .contar_texto_ciclo",
            ".contar_texto_fin:",
            "    pop esi",
            "    ret",

            "",
            "; copiar texto",
            "funcion_copiar_texto:",
            "    push eax",
            "    push ecx",
            "    cmp edx, 1",
            "    jbe .copiar_texto_vacio",
            "    mov ecx, edx",
            "    dec ecx",
            ".copiar_texto_ciclo:",
            "    cmp ecx, 0",
            "    je .copiar_texto_cero",
            "    mov al, [esi]",
            "    cmp al, 0",
            "    je .copiar_texto_cero",
            "    cmp al, 10",
            "    je .copiar_texto_cero",
            "    mov [edi], al",
            "    inc esi",
            "    inc edi",
            "    dec ecx",
            "    jmp .copiar_texto_ciclo",
            ".copiar_texto_cero:",
            "    mov byte [edi], 0",
            "    jmp .copiar_texto_salir",
            ".copiar_texto_vacio:",
            "    mov byte [edi], 0",
            ".copiar_texto_salir:",
            "    pop ecx",
            "    pop eax",
            "    ret",

            "",
            "; quitar salto de linea",
            "funcion_quitar_salto_linea:",
            "    push eax",
            ".quitar_salto_ciclo:",
            "    mov al, [esi]",
            "    cmp al, 0",
            "    je .quitar_salto_salir",
            "    cmp al, 10",
            "    je .quitar_salto_cero",
            "    inc esi",
            "    jmp .quitar_salto_ciclo",
            ".quitar_salto_cero:",
            "    mov byte [esi], 0",
            ".quitar_salto_salir:",
            "    pop eax",
            "    ret",

            "",
            "; comparar dos textos",
            "funcion_comparar_texto:",
            "    push ebx",
            ".comparar_texto_ciclo:",
            "    mov al, [esi]",
            "    mov bl, [edi]",
            "    cmp al, bl",
            "    jne .comparar_texto_distinto",
            "    cmp al, 0",
            "    je .comparar_texto_igual",
            "    inc esi",
            "    inc edi",
            "    jmp .comparar_texto_ciclo",
            ".comparar_texto_igual:",
            "    xor eax, eax",
            "    jmp .comparar_texto_salir",
            ".comparar_texto_distinto:",
            "    movzx eax, al",
            "    movzx ebx, bl",
            "    sub eax, ebx",
            ".comparar_texto_salir:",
            "    pop ebx",
            "    ret",

            "",
            "; unir dos textos",
            "funcion_unir_texto:",
            "    push ebx",
            "    push ecx",
            "    push edx",
            "    push edi",
            "    mov ebx, string_temp",
            "    mov edi, ebx",
            "    mov edx, 256",
            "    call funcion_copiar_texto",
            "    mov edi, ebx",
            ".unir_texto_buscar_fin:",
            "    cmp byte [edi], 0",
            "    je .unir_texto_pegar",
            "    inc edi",
            "    jmp .unir_texto_buscar_fin",
            ".unir_texto_pegar:",
            "    pop esi",
            "    mov edx, ebx",
            "    add edx, 255",
            "    sub edx, edi",
            "    inc edx",
            "    call funcion_copiar_texto",
            "    mov eax, ebx",
            "    pop edx",
            "    pop ecx",
            "    pop ebx",
            "    ret",
        ]

class NodoEntrada(NodoAST):
    # Nodo que representa una lectura de variable.
    def __init__(self, tipo, nombre, node_id="", label="", prompt=None):
        self.tipo = tipo
        self.nombre = nombre
        self.node_id = node_id
        self.label = label
        self.prompt = prompt

    def traducirCpp(self):
        # "Leer edad" termina como declaracion C + scanf.
        tipo = self.tipo[1] or _tipo_variable(self.nombre[1])
        nombre = self.nombre[1]
        prompt = f"{NodoPrint([self.prompt]).traducirCpp()}\n" if self.prompt else ""
        if tipo == "string":
            declaracion = f"char {nombre}[256];\n" if self.tipo[1] else ""
            return f"{prompt}{declaracion}scanf(\"%255s\", {nombre});"
        formatos = {
            "int": "%d",
            "bool": "%d",
            "float": "%f",
            "double": "%lf",
        }
        declaracion = f"{_tipo_c(tipo)} {nombre};\n" if self.tipo[1] else ""
        return f"{prompt}{declaracion}scanf(\"{formatos.get(tipo, '%d')}\", &{nombre});"

    def generarCodigo(self):
        nombre = self.nombre[1]
        tipo = self.tipo[1] or _tipo_variable(nombre)
        etiqueta_fin = NodoAST.nueva_etiqueta("fin_lectura")
        codigo = []

        if self.prompt:
            codigo.append(NodoPrint([self.prompt]).generarCodigo())

        if tipo == "string":
            codigo.extend([
                f"    ; leer string {nombre}",
                f"    mov edi, {nombre}",
                f"    mov edx, {ASM_STRING_SIZE}",
                "    call funcion_leer_linea",
                f"{etiqueta_fin}:",
            ])
            return "\n".join(codigo)

        if tipo in {"float", "double"}:
            tam = _tam_tipo_float(tipo)

            codigo.extend([
                f"    ; leer {tipo} {nombre}",
                "    mov edi, input_buffer",
                "    mov edx, 255",
                "    call funcion_leer_linea",
                "    cmp eax, 0",
                f"    jle {etiqueta_fin}",
                "    mov esi, input_buffer",
                "    call funcion_texto_a_double",
                f"    fstp {tam} [{nombre}]",
                f"{etiqueta_fin}:",
            ])
            return "\n".join(codigo)

        codigo.extend([
            f"    ; leer {nombre}",
            "    mov edi, input_buffer",
            "    mov edx, 255",
            "    call funcion_leer_linea",
            "    cmp eax, 0",
            f"    jle {etiqueta_fin}",
            "    mov esi, input_buffer",
            "    call funcion_texto_a_entero",
            f"    mov [{nombre}], eax",
            f"{etiqueta_fin}:",
        ])
        return "\n".join(codigo)

    def serializar(self):
        return {
            "tipo": "NodoEntrada",
            "node_id": self.node_id,
            "label": self.label,
            "data_type": self.tipo[1],
            "variable": self.nombre[1],
            "prompt": self.prompt.serializar() if self.prompt else None,
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
        tipo = self.tipo[1] if self.tipo is not None else NodoAST.tipos_variables.get(self.nombre[1])
        nombre = self.nombre[1]

        if tipo == "string":
            expr = self.expresion.traducirCpp()

            if self.tipo is not None:
                if isinstance(self.expresion, NodoCadena):
                    return f"char {nombre}[256] = {expr};"

                return f"char {nombre}[256];\nstrcpy({nombre}, {expr});"

            return f"strcpy({nombre}, {expr});"

        prefijo = f"{_tipo_c(self.tipo[1])} " if self.tipo is not None else ""
        return f"{prefijo}{nombre} = {self.expresion.traducirCpp()};"

    def generarCodigo(self):
        nombre = self.nombre[1]
        tipo = self.tipo[1] if self.tipo is not None else _tipo_variable(nombre)

        if tipo == "string":
            return "\n".join([
                self.expresion.generarCodigo(),
                "    mov esi, eax",
                f"    mov edi, {nombre}",
                f"    mov edx, {ASM_STRING_SIZE}",
                "    call funcion_copiar_texto",
            ])

        if tipo in {"float", "double"}:
            tam = _tam_tipo_float(tipo)

            return "\n".join([
                _gen_float(self.expresion),
                f"    fstp {tam} [{nombre}]",
            ])

        return "\n".join([
            self.expresion.generarCodigo(),
            f"    mov [{nombre}], eax",
        ])

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
        # Intenta parsear como sentencia para generar código real.
        # Si no es posible, emite comentario para no romper el ensamblado.
        from lexico import identificar_tokens
        tokens = identificar_tokens(self.expresion or "")
        try:
            nodo = ParserSentencia(
                tokens,
                node_id=self.node_id,
                label=self.label,
                codigo_original=self.expresion,
            ).parsear()
            if not isinstance(nodo, NodoProceso):
                return nodo.generarCodigo()
        except Exception:
            pass
        return f"    ; proceso no traducible: {self.expresion}"

    def serializar(self):
        return {
            "tipo": "NodoProceso",
            "node_id": self.node_id,
            "label": self.label,
            "expresion": self.expresion,
        }

class NodoExpresionSentencia(NodoAST):
    def __init__(self, expresion, node_id="", label=""):
        self.expresion = expresion
        self.node_id = node_id
        self.label = label

    def traducirCpp(self):
        return f"{self.expresion.traducirCpp()};"

    def generarCodigo(self):
        return self.expresion.generarCodigo()

    def serializar(self):
        return {
            "tipo": "NodoExpresionSentencia",
            "node_id": self.node_id,
            "label": self.label,
            "expresion": self.expresion.serializar(),
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
        codigo = [_gen_bool(self.condicion), "    cmp eax, 0", f"    je {etiqueta_sino}"]
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
        codigo = [f"{etiqueta_inicio}:", _gen_bool(self.condicion), "    cmp eax, 0", f"    je {etiqueta_fin}"]
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
            _gen_bool(self.condicion),
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
        if not self.argumentos:
            return "\n".join([
                "    mov eax, 4",
                "    mov ebx, 1",
                "    mov ecx, newline",
                "    mov edx, 1",
                "    int 0x80",
            ])

        lineas = []

        for indice, argumento in enumerate(self.argumentos):
            tipo = _tipo_expr(argumento)

            if tipo == "string":
                lineas.extend([
                    argumento.generarCodigo(),
                    "    mov esi, eax",
                    "    call funcion_contar_texto",
                    "    mov edx, eax",
                    "    mov eax, 4",
                    "    mov ebx, 1",
                    "    mov ecx, esi",
                    "    int 0x80",
                ])

            elif tipo in {"float", "double"}:
                lineas.extend([
                    _gen_float(argumento),
                    "    mov esi, print_buffer",
                    "    call funcion_double_a_texto",
                    "    mov edx, eax",
                    "    mov eax, 4",
                    "    mov ebx, 1",
                    "    mov ecx, print_buffer",
                    "    int 0x80",
                ])

            else:
                lineas.extend([
                    argumento.generarCodigo(),
                    "    mov esi, print_buffer",
                    "    call funcion_entero_a_texto",
                    "    mov edx, eax",
                    "    mov eax, 4",
                    "    mov ebx, 1",
                    "    mov ecx, print_buffer",
                    "    int 0x80",
                ])

            if indice < len(self.argumentos) - 1:
                lineas.extend([
                    "    mov eax, 4",
                    "    mov ebx, 1",
                    "    mov ecx, space_chr",
                    "    mov edx, 1",
                    "    int 0x80",
                ])

        if self.salto_linea:
            lineas.extend([
                "    mov eax, 4",
                "    mov ebx, 1",
                "    mov ecx, newline",
                "    mov edx, 1",
                "    int 0x80",
            ])

        return "\n".join(lineas)

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
        tipo_i = _tipo_expr(self.izquierda)
        tipo_d = _tipo_expr(self.derecha)
        op = self.operador[1]

        if op in {"&&", "||"}:
            if op == "&&":
                return "\n".join([
                    _gen_bool(self.izquierda),
                    "    push eax",
                    _gen_bool(self.derecha),
                    "    mov ebx, eax",
                    "    pop eax",
                    "    cmp eax, 0",
                    "    setne al",
                    "    cmp ebx, 0",
                    "    setne bl",
                    "    and al, bl",
                    "    movzx eax, al",
                ])

            return "\n".join([
                _gen_bool(self.izquierda),
                "    push eax",
                _gen_bool(self.derecha),
                "    mov ebx, eax",
                "    pop eax",
                "    or eax, ebx",
                "    setne al",
                "    movzx eax, al",
            ])

        if tipo_i == "string" or tipo_d == "string":
            if op == "+":
                if tipo_i != "string" or tipo_d != "string":
                    raise Exception(
                        "El operador + con string en ASM requiere que ambos operandos sean string."
                    )

                return "\n".join([
                    self.izquierda.generarCodigo(),
                    "    push eax",
                    self.derecha.generarCodigo(),
                    "    mov edi, eax",
                    "    pop esi",
                    "    call funcion_unir_texto",
                ])

            if op in {"==", "!="}:
                if tipo_i != "string" or tipo_d != "string":
                    raise Exception(
                        "La comparación string en ASM requiere que ambos operandos sean string."
                    )

                salto = "sete" if op == "==" else "setne"

                return "\n".join([
                    self.izquierda.generarCodigo(),
                    "    push eax",
                    self.derecha.generarCodigo(),
                    "    mov edi, eax",
                    "    pop esi",
                    "    call funcion_comparar_texto",
                    "    cmp eax, 0",
                    f"    {salto} al",
                    "    movzx eax, al",
                ])

            raise Exception(f"Operador no soportado para string en ASM: {op}")

        if _es_tipo_float(tipo_i) or _es_tipo_float(tipo_d):
            if op in {"+", "-", "*", "/"}:
                return "\n".join([
                    self.generarCodigoFloat(),
                    "    fistp dword [tmp_int]",
                    "    mov eax, [tmp_int]",
                ])

            if op in {">", "<", ">=", "<=", "==", "!="}:
                rel = {
                    ">": "seta",
                    "<": "setb",
                    ">=": "setae",
                    "<=": "setbe",
                    "==": "sete",
                    "!=": "setne",
                }[op]

                return "\n".join([
                    _gen_float(self.izquierda),
                    _gen_float(self.derecha),
                    "    fxch st1",
                    "    fcomip st0, st1",
                    "    fstp st0",
                    f"    {rel} al",
                    "    movzx eax, al",
                ])

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

        if op in aritmeticos:
            codigo.append(aritmeticos[op])

        elif op == "/":
            codigo.extend([
                "    cdq",
                "    idiv ebx",
            ])

        elif op == "%":
            codigo.extend([
                "    cdq",
                "    idiv ebx",
                "    mov eax, edx",
            ])

        elif op in relacionales:
            codigo.extend([
                "    cmp eax, ebx",
                f"    {relacionales[op]} al",
                "    movzx eax, al",
            ])

        else:
            codigo.append(f"    ; operador no implementado: {op}")

        return "\n".join(codigo)


    def generarCodigoFloat(self):
        op = self.operador[1]

        if op not in {"+", "-", "*", "/"}:
            return "\n".join([
                self.generarCodigo(),
                "    mov [tmp_int], eax",
                "    fild dword [tmp_int]",
            ])

        codigo = [
            _gen_float(self.izquierda),
            _gen_float(self.derecha),
        ]

        if op == "+":
            codigo.append("    faddp st1, st0")
        elif op == "-":
            codigo.append("    fsubp st1, st0")
        elif op == "*":
            codigo.append("    fmulp st1, st0")
        elif op == "/":
            codigo.append("    fdivp st1, st0")

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
        tipo = _tipo_expr(self.expresion)

        if self.operador[1] == "!":
            return "\n".join([
                _gen_bool(self.expresion),
                "    cmp eax, 0",
                "    sete al",
                "    movzx eax, al",
            ])

        if self.operador[1] == "-" and _es_tipo_float(tipo):
            return "\n".join([
                _gen_float(self.expresion),
                "    fchs",
                "    fistp dword [tmp_int]",
                "    mov eax, [tmp_int]",
            ])

        codigo = [self.expresion.generarCodigo()]

        if self.operador[1] == "-":
            codigo.append("    neg eax")

        return "\n".join(codigo)


    def generarCodigoFloat(self):
        if self.operador[1] == "!":
            return "\n".join([
                self.generarCodigo(),
                "    mov [tmp_int], eax",
                "    fild dword [tmp_int]",
            ])

        codigo = [_gen_float(self.expresion)]

        if self.operador[1] == "-":
            codigo.append("    fchs")

        return "\n".join(codigo)

    def serializar(self):
        return {
            "tipo": "NodoUnario",
            "operador": self.operador[1],
            "expresion": self.expresion.serializar(),
        }


class NodoLlamadaFuncion(NodoAST):
    def __init__(self, nombre_funcion, argumentos):
        self.nombre_funcion = nombre_funcion
        self.argumentos = argumentos

    def traducirCpp(self):
        args = ", ".join(a.traducirCpp() for a in self.argumentos)
        return f"{self.nombre_funcion}({args})"

    def _generar_push_argumentos(self):
        lineas = []
        bytes_args = 0

        for argumento in reversed(self.argumentos):
            tipo = _tipo_expr(argumento)

            if tipo in {"float", "double"}:
                lineas.extend([
                    _gen_float(argumento),
                    "    sub esp, 8",
                    "    fstp qword [esp]",
                ])
                bytes_args += 8

            elif tipo == "string":
                lineas.extend([
                    argumento.generarCodigo(),
                    "    push eax",
                ])
                bytes_args += 4

            else:
                lineas.extend([
                    argumento.generarCodigo(),
                    "    push eax",
                ])
                bytes_args += 4

        return lineas, bytes_args

    def generarCodigo(self):
        nombre = self.nombre_funcion

        if nombre in {"len", "strlen", "length"}:
            if not self.argumentos:
                return "    mov eax, 0"

            return "\n".join([
                self.argumentos[0].generarCodigo(),
                "    mov esi, eax",
                "    call funcion_contar_texto",
            ])

        if nombre == "concat" and len(self.argumentos) >= 2:
            return "\n".join([
                self.argumentos[0].generarCodigo(),
                "    push eax",
                self.argumentos[1].generarCodigo(),
                "    mov edi, eax",
                "    pop esi",
                "    call funcion_unir_texto",
            ])

        if nombre == "abs" and self.argumentos and not _es_tipo_float(_tipo_expr(self.argumentos[0])):
            etiqueta = NodoAST.nueva_etiqueta("abs_fin")

            return "\n".join([
                self.argumentos[0].generarCodigo(),
                "    cmp eax, 0",
                f"    jge {etiqueta}",
                "    neg eax",
                f"{etiqueta}:",
            ])

        if nombre == "int" and self.argumentos:
            if _es_tipo_float(_tipo_expr(self.argumentos[0])):
                return "\n".join([
                    _gen_float(self.argumentos[0]),
                    "    fistp dword [tmp_int]",
                    "    mov eax, [tmp_int]",
                ])

            return self.argumentos[0].generarCodigo()

        if nombre in {"float", "double"} and self.argumentos:
            return "\n".join([
                _gen_float(self.argumentos[0]),
                "    fistp dword [tmp_int]",
                "    mov eax, [tmp_int]",
            ])

        if nombre in {"max", "min"} and len(self.argumentos) >= 2:
            if _es_tipo_float(_tipo_expr(self.argumentos[0])) or _es_tipo_float(_tipo_expr(self.argumentos[1])):
                return "\n".join([
                    self.generarCodigoFloat(),
                    "    fistp dword [tmp_int]",
                    "    mov eax, [tmp_int]",
                ])

            etiqueta = NodoAST.nueva_etiqueta(f"{nombre}_fin")
            salto = "jge" if nombre == "max" else "jle"

            return "\n".join([
                self.argumentos[0].generarCodigo(),
                "    push eax",
                self.argumentos[1].generarCodigo(),
                "    mov ebx, eax",
                "    pop eax",
                "    cmp eax, ebx",
                f"    {salto} {etiqueta}",
                "    mov eax, ebx",
                f"{etiqueta}:",
            ])

        lineas, bytes_args = self._generar_push_argumentos()
        lineas.append(f"    call {nombre}")

        if bytes_args:
            lineas.append(f"    add esp, {bytes_args}")

        return "\n".join(lineas)

    def generarCodigoFloat(self):
        nombre = self.nombre_funcion

        if nombre in {"float", "double"} and self.argumentos:
            return _gen_float(self.argumentos[0])

        if nombre in {"sqrt", "sin", "cos", "abs"} and self.argumentos:
            codigo = [_gen_float(self.argumentos[0])]

            if nombre == "sqrt":
                codigo.append("    fsqrt")
            elif nombre == "sin":
                codigo.append("    fsin")
            elif nombre == "cos":
                codigo.append("    fcos")
            elif nombre == "abs":
                codigo.append("    fabs")

            return "\n".join(codigo)

        if nombre in {"max", "min"} and len(self.argumentos) >= 2:
            et_true = NodoAST.nueva_etiqueta(f"{nombre}_f_true")
            et_fin = NodoAST.nueva_etiqueta(f"{nombre}_f_fin")
            salto = "jae" if nombre == "max" else "jbe"

            return "\n".join([
                _gen_float(self.argumentos[0]),
                _gen_float(self.argumentos[1]),
                "    fxch st1",
                "    fcomip st0, st1",
                f"    {salto} {et_true}",
                f"    jmp {et_fin}",
                f"{et_true}:",
                "    fstp st0",
                _gen_float(self.argumentos[0]),
                f"{et_fin}:",
            ])

        lineas, bytes_args = self._generar_push_argumentos()
        lineas.append(f"    call {nombre}")

        if bytes_args:
            lineas.append(f"    add esp, {bytes_args}")

        return "\n".join(lineas)

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
        nombre = self.nombre[1]
        tipo = _tipo_variable(nombre)

        if tipo == "string":
            return f"    mov eax, {nombre}"

        if tipo in {"float", "double"}:
            tam = _tam_tipo_float(tipo)

            return "\n".join([
                f"    fld {tam} [{nombre}]",
                "    fistp dword [tmp_int]",
                "    mov eax, [tmp_int]",
            ])

        return f"    mov eax, [{nombre}]"


    def generarCodigoFloat(self):
        nombre = self.nombre[1]
        tipo = _tipo_variable(nombre)

        if tipo in {"float", "double"}:
            tam = _tam_tipo_float(tipo)
            return f"    fld {tam} [{nombre}]"

        return "\n".join([
            f"    mov eax, [{nombre}]",
            "    mov [tmp_int], eax",
            "    fild dword [tmp_int]",
        ])

    def serializar(self):
        return {"tipo": "NodoIdentificador", "nombre": self.nombre[1]}


class NodoNumero(NodoAST):
    # Nodo que representa a un numero.
    def __init__(self, valor):
        self.valor = valor

    def traducirCpp(self):
        return self.valor[1]

    def generarCodigo(self):
        if _es_float_literal(self.valor[1]):
            etiqueta = getattr(self, "etiqueta_float", None)

            if etiqueta is None:
                return f"    ; ERROR: literal float sin etiqueta: {self.valor[1]}"

            return "\n".join([
                f"    fld qword [{etiqueta}]",
                "    fistp dword [tmp_int]",
                "    mov eax, [tmp_int]",
            ])

        return f"    mov eax, {self.valor[1]}"


    def generarCodigoFloat(self):
        if _es_float_literal(self.valor[1]):
            etiqueta = getattr(self, "etiqueta_float", None)

            if etiqueta is None:
                return f"    ; ERROR: literal float sin etiqueta: {self.valor[1]}"

            return f"    fld qword [{etiqueta}]"

        return "\n".join([
            f"    mov dword [tmp_int], {self.valor[1]}",
            "    fild dword [tmp_int]",
        ])

    def serializar(self):
        return {"tipo": "NodoNumero", "valor": self.valor[1]}


class NodoCadena(NodoAST):
    # Nodo que representa a una cadena.
    def __init__(self, valor):
        self.valor = valor

    def traducirCpp(self):
        return self.valor[1]

    def generarCodigo(self):
        etiqueta = getattr(self, "etiqueta", None)

        if etiqueta is None:
            return "    ; ERROR: cadena sin etiqueta asignada\n    mov eax, 0"

        return f"    mov eax, {etiqueta}"

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
            fin = self.pos
            while fin < len(self.tokens) and self.tokens[fin][1] != ";":
                fin += 1

            try:
                expresion = ParserExpresion(self.tokens[self.pos:fin]).parsear()
                self.pos = fin

                if isinstance(expresion, NodoLlamadaFuncion):
                    nodo = NodoExpresionSentencia(
                        expresion,
                        node_id=self.node_id,
                        label=self.label
                    )
                else:
                    return NodoProceso(
                        self.codigo_original,
                        node_id=self.node_id,
                        label=self.label
                    )
            except Exception:
                return NodoProceso(
                    self.codigo_original,
                    node_id=self.node_id,
                    label=self.label
                )

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
            data_type = data.get("dataType")
            prompt = self._texto(data, "prompt", "message")

            if not data_type:
                data_type = data.get("data_type")

            tipo_texto, variable_texto, tipo_explicito, prompt_texto = self._parsear_texto_entrada(texto_figura)

            if not prompt:
                prompt = prompt_texto

            if not variable:
                variable = variable_texto

            tipos_validos = {"int", "float", "double", "bool", "string"}

            if data_type:
                data_type = str(data_type).strip().lower()

            # Si el texto dice explícitamente "string nombre", gana el texto.
            if tipo_explicito:
                data_type = tipo_texto

            # Si no hay tipo, se interpreta como lectura de una variable ya creada.
            elif not data_type:
                data_type = ""
            elif data_type not in tipos_validos:
                data_type = tipo_texto

            return NodoEntrada(
                ("KEYWORD", data_type),
                ("IDENTIFIER", variable),
                node_id=node_id,
                label=label,
                prompt=self._parsear_prompt_entrada(prompt) if prompt else None,
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
        # Devuelve (tipo, variable, tipo_explicito, prompt).
        # tipo_explicito=True cuando el usuario escribió:
        #   "Leer string nombre"
        #   "string nombre"
        #   "input float nota"
        #
        # Si solo dice "nombre", no inferimos tipo: la entrada debe traer tipo.

        tipos = {"int", "float", "double", "bool", "string"}
        prefijos = {"leer", "input", "ingresar", "ingresa"}
        nombres_string = {
            "nombre",
            "apellido",
            "texto",
            "cadena",
            "mensaje",
            "usuario",
            "correo",
            "email",
        }

        prompt, entrada = self._separar_prompt_entrada(texto or "")
        partes = entrada.strip().split()

        if not partes:
            return "", "", False, prompt

        if partes[0].lower() in prefijos:
            partes = partes[1:]

        # Para casos como: "Ingresa tu nombre"
        if partes and partes[0].lower() == "tu":
            partes = partes[1:]

        if not partes:
            return "", "", False, prompt

        if partes[0].lower() in tipos:
            tipo = partes[0].lower()
            variable = partes[1] if len(partes) >= 2 else ""
            return tipo, variable, True, prompt

        return "", partes[-1], False, prompt

    def _separar_prompt_entrada(self, texto):
        partes = self._separar_por_comas(texto)
        if len(partes) >= 2 and partes[0].strip().startswith('"'):
            return partes[0].strip(), ",".join(partes[1:]).strip()
        return "", texto

    def _parsear_prompt_entrada(self, prompt):
        prompt = str(prompt).strip()
        if not prompt:
            return None
        if prompt.startswith('"') and prompt.endswith('"'):
            return NodoCadena(("STRING", prompt))
        return self._parsear_expresion(prompt)

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
