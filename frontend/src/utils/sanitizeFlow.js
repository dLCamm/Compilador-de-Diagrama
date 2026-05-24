const TIPOS_VALIDOS = new Set(["int", "float", "double", "bool", "string"]);

function parsearEntrada(valor = "") {
    const texto = String(valor).trim();
    const partesEntrada = separarMensajeEntrada(texto);
    const mensaje = partesEntrada.mensaje;
    const entrada = partesEntrada.entrada;
    const partes = entrada.split(/\s+/);

    if (partes.length >= 2 && TIPOS_VALIDOS.has(partes[0])) {
        return {
            prompt: mensaje,
            dataType: partes[0],
            variable: partes[1]
        };
    }

    return {
        prompt: mensaje,
        dataType: "",
        variable: entrada
    };
}

function separarMensajeEntrada(texto) {
    let enCadena = false;
    let escape = false;

    for (let i = 0; i < texto.length; i += 1) {
        const caracter = texto[i];

        if (escape) {
            escape = false;
            continue;
        }

        if (caracter === "\\") {
            escape = true;
            continue;
        }

        if (caracter === '"') {
            enCadena = !enCadena;
            continue;
        }

        if (caracter === "," && !enCadena) {
            return {
                mensaje: texto.slice(0, i).trim(),
                entrada: texto.slice(i + 1).trim()
            };
        }
    }

    return {
        mensaje: "",
        entrada: texto
    };
}

export function sanitizeFlow(nodes, edges) {

    const cleanNodes = nodes.map((node) => {

        // START / END

        if (
            node.type === "start" ||
            node.type === "end"
        ) {

            return {
                id: node.id,

                type: node.type,

                data: {
                    label: node.data.label
                }
            };
        }

        // PROCESS

        if (node.type === "process") {

            return {
                id: node.id,

                type: node.type,

                data: {
                    label: node.data.code,
                    code: node.data.code
                }
            };
        }

        // CONDITION

        if (node.type === "condition") {

            return {
                id: node.id,

                type: node.type,

                data: {
                    label: node.data.expression,
                    expression:
                        node.data.expression
                }
            };
        }

        // INPUT

        if (node.type === "input") {

            const entrada =
                parsearEntrada(node.data.variable);

            return {
                id: node.id,

                type: node.type,

                data: {
                    label:
                        `Leer ${[entrada.prompt, entrada.dataType, entrada.variable].filter(Boolean).join(" ")}`,

                    variable:
                        entrada.variable,

                    dataType:
                        entrada.dataType,

                    prompt:
                        entrada.prompt
                }
            };
        }

        // OUTPUT

        if (node.type === "output") {

            return {
                id: node.id,

                type: node.type,

                data: {
                    label:
                        `Mostrar ${node.data.expression}`,

                    expression:
                        node.data.expression
                }
            };
        }

        return node;
    });

    // EDGES

    const cleanEdges = edges.map((edge) => {

        const cleanEdge = {

            id: edge.id,

            source: edge.source,

            target: edge.target,

            type: "control"
        };

        // TRUE / FALSE

        if (edge.sourceHandle) {

            cleanEdge.sourceHandle =
                edge.sourceHandle;
        }

        // LABELS

        if (edge.label) {

            cleanEdge.data = {
                label: edge.label
            };
        }

        return cleanEdge;
    });

    // JSON FINAL

    return {

        version: "1.0.0",

        languageTarget: "c",

        flow: {

            nodes: cleanNodes,

            edges: cleanEdges
        }
    };
}
