import { useState } from "react";
import DiagramCanvas from "./components/canvas/DiagramCanvas";
import CodePanel from "./components/codigo/CodePanel";
import { sanitizeFlow } from "./utils/sanitizeFlow";
import "./App.css";


function App() {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [cppCode, setCppCode] = useState("");

  const handleCompile = async () => {
    try {

      const flowJSON =
        sanitizeFlow(nodes, edges);

      console.log(flowJSON);
      // EL flowJSON es el que tenes que agarrar Carlos

    } catch (error) {

      console.error(error);
    }
  };

  return (

    <div className="forminicial">

      <div className="encabezado">

        <div style={{width:"15%",height: "100%",display: "flex",alignItems: "flex-end"}}>

          <h1 className="titulo">ELEMENTOS</h1>

        </div>

        <div style={{width:"52.5%",display: "flex",justifyContent: "right",alignItems: "flex-end",height: "100%"}}>

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

        />

        <div className="codigos">

          <CodePanel cppCode={cppCode} />

        </div>

      </div>

    </div>
  );
}

export default App;