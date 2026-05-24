import { useRef, useState } from "react";
import DiagramCanvas from "./components/canvas/DiagramCanvas";
import CodePanel from "./components/codigo/CodePanel";
import { compilarDiagrama } from "./services/compilador";
import { sanitizeFlow } from "./utils/sanitizeFlow";
import "./App.css";


function App() {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [codigoC, setCodigoC] = useState("");
  const [assembler, setAssembler] = useState("");
  const [echo, setEcho] = useState([]);
  const [eventosEcho, setEventosEcho] = useState([]);
  const [compileStatus, setCompileStatus] = useState("idle");
  const [compileError, setCompileError] = useState("");
  const ordenEcho = useRef(0);

  const siguienteOrdenEcho = () => {
    ordenEcho.current += 1;
    return ordenEcho.current;
  };

  const agregarEventoEcho = (mensaje) => {
    setEventosEcho((eventos) => [
      ...eventos,
      {
        stage: "front",
        mensaje,
        tipo: "ui",
        time: new Date().toISOString(),
        order: siguienteOrdenEcho(),
      },
    ].slice(-80));
  };

  const agregarHoraEchoBackend = (pasos = []) => {
    const base = Date.now();

    return pasos.map((paso, index) => ({
      ...paso,
      time: new Date(base + index).toISOString(),
      order: siguienteOrdenEcho(),
    }));
  };

  const handleCompile = async () => {
    setCompileStatus("loading");
    setCompileError("");
    setEcho([]);

    try {
      const flowJSON =
        sanitizeFlow(nodes, edges);

      agregarEventoEcho("Se envio el diagrama al backend");

      const respuesta =
        await compilarDiagrama(flowJSON);

      const resultado = respuesta.resultado || {};

      if (!respuesta.ok) {
        setCodigoC("");
        setAssembler("");
        setEcho(agregarHoraEchoBackend(resultado.echo || []));
        setCompileError(
          respuesta.errores?.[0] ||
          respuesta.mensaje ||
          "No se pudo compilar el diagrama."
        );
        setCompileStatus("error");
        agregarEventoEcho("El backend respondio con errores");
        return;
      }

      setCodigoC(resultado.codigoC || "");
      setAssembler(resultado.assembler || "");
      setEcho(agregarHoraEchoBackend(resultado.echo || []));
      setCompileStatus("ready");
      agregarEventoEcho("El backend termino la compilacion");

    } catch (error) {
      setCodigoC("");
      setAssembler("");
      setCompileError(error.message || "No se pudo conectar con el backend.");
      setCompileStatus("error");
      agregarEventoEcho("No se pudo conectar con el backend");
      console.error(error);
    }
  };

  const limpiarDiagrama = () => {
    setNodes([]);
    setEdges([]);
    setCodigoC("");
    setAssembler("");
    setEcho([]);
    setCompileError("");
    setCompileStatus("idle");
    agregarEventoEcho("Diagrama limpiado");
  };

  return (

    <div className="forminicial">

      <div className="encabezado">

        <div style={{width:"15%",height: "100%",display: "flex",alignItems: "flex-end"}}>

          <h1 className="titulo">ELEMENTOS</h1>

        </div>

        <div style={{width:"52.5%",display: "flex",justifyContent: "right",alignItems: "flex-end",height: "100%", gap: "12px"}}>

          <button className="boton boton-icono" onClick={limpiarDiagrama} title="Limpiar diagrama">
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 12a9 9 0 0 1-15.3 6.4" />
              <path d="M3 12A9 9 0 0 1 18.3 5.6" />
              <path d="M6 18H3v3" />
              <path d="M18 6h3V3" />
            </svg>
          </button>

          <button className="boton" onClick={handleCompile}>
            Generar Código
          </button>

        </div>

        <div style={{width:"29.5%", height: "100%", display: "flex", alignItems: "flex-end"}}>
          <h1 className="titulo">CODIGO</h1>
        </div>

      </div>

      <div className="funciones">

        <DiagramCanvas

          nodes={nodes}
          setNodes={setNodes}

          edges={edges}
          setEdges={setEdges}
          onEchoEvent={agregarEventoEcho}

        />

        <div className="codigos">

          <CodePanel
            codigoC={codigoC}
            assembler={assembler}
            echo={echo}
            eventos={eventosEcho}
            status={compileStatus}
            error={compileError}
            onEchoEvent={agregarEventoEcho}
          />

        </div>

      </div>

    </div>
  );
}

export default App;
