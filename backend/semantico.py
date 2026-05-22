# Analizador semantico: variables, tipos y reglas del programa.
from sintactico_ast import *


class TablaSimbolos:
    def __init__(self):
        self.variables = {} # Almacena variables {nombre: tipo}
        self.funciones = {} # Almacena funciones {nombre: (tipo_retorno, [parametros])}
        self.cadenas = {} # Almacena cadenas {nombre: valor}
        self.flotantes = {}

    def modificar_cadena(self, nombre, valor):
        if nombre in self.cadenas:
            self.cadenas[nombre] = valor

    def declarar_flotante(self, nombre, valor):
        if nombre in self.flotantes:
            raise Exception(f"Error: Numero '{nombre}' ya declarado")
        self.flotantes[nombre] = valor
    def declarar_cadena(self, nombre, valor):
        if nombre in self.cadenas:
            raise Exception(f"Error: Cadena '{nombre}' ya declarada")
        self.cadenas[nombre] = valor

    def declarar_variable(self, nombre, tipo):
        if nombre in self.variables:
            raise Exception(f"Error: Variable '{nombre}' ya declarada")
        self.variables[nombre] = tipo

    def obtener_tipo_variable(self, nombre):
        if nombre not in self.variables:
            raise Exception(f"Error: Variable '{nombre}' no declarada")
        return self.variables[nombre]

    def declarar_funcion(self, nombre, tipo_retorno, parametros):
        if nombre in self.funciones:
            raise Exception(f"Error: Función '{nombre}' ya declarada")
        self.funciones[nombre] = (tipo_retorno, parametros)
    
    def obtener_info_funcion(self, nombre):
        if nombre not in self.funciones:
            raise Exception(f"Error: Función '{nombre}' no declarada")
        return self.funciones[nombre]

# start llama a main

class AnalizadorSemantico:
    def __init__(self):
        self.tabla_simbolos = TablaSimbolos()
        self.contador_cadenas = 0
    def analizar(self, nodo):
        if isinstance(nodo, NodoAsignacion):
            tipo_expr = self.analizar(nodo.expresion)
            # Verificar si la variable ya existe (puede ser un parámetro)
            if nodo.nombre[1] not in self.tabla_simbolos.variables:
                self.tabla_simbolos.declarar_variable(nodo.nombre[1], tipo_expr)
            else:
                tipo_existente = self.tabla_simbolos.obtener_tipo_variable(nodo.nombre[1])
                if tipo_existente != tipo_expr:
                    raise Exception(f"Error: Tipo incompatible en asignación para '{nodo.nombre[1]}' (esperaba {tipo_existente}, recibió {tipo_expr})")
        elif isinstance(nodo, NodoPrint):
            if isinstance(nodo.variable, NodoCadena):
                nombre_cadena = f"cadena_{self.contador_cadenas}"
                self.contador_cadenas += 1
                self.tabla_simbolos.declarar_cadena(nombre_cadena, nodo.variable.valor)
                nodo.variable = NodoIdentificador(('IDENTIFIER', nombre_cadena), 'str')  
            elif isinstance(nodo.variable, NodoIdentificador):
                # Verificar si la variable existe
                tipo = self.tabla_simbolos.obtener_tipo_variable(nodo.variable.nombre[1])
                if tipo == 'str':
                    nodo.variable.tipo = 'str'
                elif tipo == 'int':
                    nodo.variable.tipo = 'int'
                elif tipo == 'float':
                    nodo.variable.tipo = 'float'
                elif tipo == 'char':
                    nodo.variable.tipo = 'char'
                else:
                    raise Exception(f"Error: Tipo de variable '{nodo.variable.nombre[1]}' no soportado en print")            

        elif isinstance(nodo, NodoNumero):
            # Comprobar si el número es entero o decimal
            if isinstance(nodo.valor, int):
                return "int"
            elif isinstance(nodo.valor, float):
                const_float = f"const_float_{str(nodo.valor).replace('.', '_')}"
                self.tabla_simbolos.declarar_flotante(const_float, nodo.valor)
                self.tabla_simbolos.declarar_variable(const_float, 'float')
                return "float"
            return "int"  # Por defecto, consideramos que es un entero


        elif isinstance(nodo, NodoPrintList): # NodoPrintList es una lista que contiene varios NodoPrint
            for variablePrint in nodo.variables:
                self.analizar(variablePrint)


        elif isinstance(nodo, NodoDeclaracionVariable):
            # Verificar si la variable ya existe
            if nodo.nombre[1] in self.tabla_simbolos.variables:
                raise Exception(f"Error: Variable '{nodo.nombre[1]}' ya declarada")
            # Declarar la variable en la tabla de símbolos
            self.tabla_simbolos.declarar_variable(nodo.nombre[1], nodo.tipo)
        elif isinstance(nodo, NodoIdentificador):
            if nodo.tipo == 'None':
                tipo = self.tabla_simbolos.obtener_tipo_variable(nodo.nombre[1])
                nodo.tipo = tipo
            return self.tabla_simbolos.obtener_tipo_variable(nodo.nombre[1])

        elif isinstance(nodo, NodoCadena):
            return "str"
        elif isinstance(nodo, NodoAsignacionCadena):
            nombre_cadena = nodo.nombre[1]
            cadena = nodo.expresion
            # Verificar si la cadena ya existe
            if nombre_cadena in self.tabla_simbolos.cadenas:
                self.tabla_simbolos.modificar_cadena(nombre_cadena, cadena)
            else:
                self.tabla_simbolos.declarar_cadena(nombre_cadena, cadena)
                self.tabla_simbolos.declarar_variable(nombre_cadena, 'str')
        elif isinstance(nodo, NodoOperacion):
            new = nodo.simplificar()
            tipo_izq = self.analizar(new.izquierda)
            tipo_der = self.analizar(new.derecha)
            if tipo_izq == tipo_der:
                nodo.tipo = tipo_izq
                return tipo_izq
            elif 'float' in [tipo_izq, tipo_der] and 'int' in [tipo_izq, tipo_der]:
                nodo.tipo = 'float'
                return 'float'
            else:
                raise Exception(f"Error: Tipos incompatibles en operación: {tipo_izq} {nodo.operador[1]} {tipo_der}")

        elif isinstance(nodo, NodoFuncion):
            # Registrar la función en la tabla de símbolos
            self.tabla_simbolos.declarar_funcion(nodo.nombre[1], nodo.tipo_retorno[1], nodo.parametros)

            # Registrar los parámetros en la tabla de variables
            for param in nodo.parametros:
                self.tabla_simbolos.declarar_variable(param.nombre[1], param.tipo[1])            
            # Analizar el cuerpo de la función
            for instruccion in nodo.cuerpo:
                self.analizar(instruccion)
        elif isinstance(nodo, NodoIf):
            tipo_condicion = self.analizar(nodo.condicion)
            if tipo_condicion != 'int':
                raise Exception(f"Error: Tipo de condición no válida en if (esperado 'int', recibido '{tipo_condicion}')")
            # Analizar el cuerpo del if
            for instruccion in nodo.cuerpo:
                self.analizar(instruccion)
            # Analizar el cuerpo del else (si existe)
            if nodo.sino:
                for instruccion in nodo.sino:
                    self.analizar(instruccion)
        elif isinstance(nodo, NodoWhile):
            # Analizar la condición
            tipo_condicion = self.analizar(nodo.condicion)
            if tipo_condicion != 'int':
                raise Exception(f"Error: Tipo de condición no válida en while (esperado 'int', recibido '{tipo_condicion}')")
            # Analizar el cuerpo del while
            for instruccion in nodo.cuerpo:
                self.analizar(instruccion)

                
        elif isinstance(nodo, NodoLlamadaFuncion):
            tipo_retorno, parametros = self.tabla_simbolos.obtener_info_funcion(nodo.nombre[1])
            if len(nodo.argumentos) != len(parametros):
                raise Exception(f"Error: La función '{nodo.nombre[1]}' espera {len(parametros)} argumentos, pero recibió {len(nodo.argumentos)}")
            return tipo_retorno
        elif isinstance(nodo, NodoPrograma):
            for funcion in nodo.funciones:
                self.analizar(funcion)
        elif isinstance(nodo, NodoInput):
            # Verificar si la variable existe
            if isinstance(nodo.variable, NodoIdentificador):
                tipo = self.tabla_simbolos.obtener_tipo_variable(nodo.variable.nombre[1])
                # Cambiar el tipo de la variable a 'int' o 'str' dependiendo de la entrada del texto
                if tipo == 'int':
                    nodo.variable.tipo = 'int'
                elif tipo == 'str':
                    nodo.variable.tipo = 'str'
                elif tipo == 'float':
                    nodo.variable.tipo = 'float'
                elif tipo == 'char':
                    nodo.variable.tipo = 'char'
                else:
                    raise Exception(f"Error: Tipo de variable '{nodo.variable.nombre[1]}' no soportado en input")
                
            else:
                raise Exception(f"Error: La variable '{nodo.variable}' no está declarada")
        elif isinstance(nodo, NodoRetorno):
            tipo_expr = self.analizar(nodo.expresion)

