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
      const entrada = parsearEntrada(node.data.variable);

      cleanNode.data = {
        label: `Leer ${[entrada.prompt, entrada.dataType, entrada.variable].filter(Boolean).join(" ")}`,
        variable: entrada.variable,
        dataType: entrada.dataType,
        prompt: entrada.prompt
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
