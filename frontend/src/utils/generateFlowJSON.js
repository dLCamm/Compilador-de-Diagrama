export function generateFlowJSON(nodes, edges) {

  const cleanNodes = nodes.map((node) => {

    const cleanNode = {
      id: node.id,
      type: node.type,
      data: {}
    };

    if (
      node.type === "start" ||
      node.type === "end"
    ) {

      cleanNode.data = {
        label: node.data.label
      };
    }


    if (node.type === "process") {

      cleanNode.data = {
        label: node.data.code,
        code: node.data.code
      };
    }


    if (node.type === "input") {

      cleanNode.data = {
        label: `Leer ${node.data.variable}`,
        variable: node.data.variable,
        dataType: "int"
      };
    }

    if (node.type === "output") {

      cleanNode.data = {
        label: `Mostrar ${node.data.expression}`,
        expression: node.data.expression
      };
    }



    if (node.type === "condition") {

      cleanNode.data = {
        label: node.data.expression,
        expression: node.data.expression
      };
    }

    return cleanNode;
  });


  const cleanEdges = edges.map((edge) => {

    const cleanEdge = {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: "control"
    };

    // true / false

    if (edge.sourceHandle) {

      cleanEdge.sourceHandle =
        edge.sourceHandle;
    }

    // Sí / No

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
