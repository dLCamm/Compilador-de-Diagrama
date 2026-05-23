# Generacion de codigo delegada al AST, siguiendo el estilo del compilador de referencia.


def generar_cpp(programa):
    # El nombre queda por compatibilidad, pero el AST genera C real.
    return programa.traducirCpp()


def generar_assembler(programa):
    # La generacion assembler tambien vive en los nodos del AST.
    return programa.generarCodigo()
