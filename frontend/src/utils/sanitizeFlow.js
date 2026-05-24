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

            return {
                id: node.id,

                type: node.type,

                data: {
                    label:
                        `Leer ${node.data.variable}`,

                    variable:
                        node.data.variable,

                    dataType: "int"
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
