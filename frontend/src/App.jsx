import DiagramCanvas from "./components/canvas/DiagramCanvas";
import CodePanel from "./components/codigo/CodePanel";
import "./App.css";

function App() {

  return (
  <div className="forminicial">
    <div className ="encabezado">
      <div style={{ width:"15%",  height: "100%", display: "flex",  alignItems: "flex-end" }}><h1 className="titulo">ELEMENTOS</h1></div>
      <div style={{ width:"52.5%", display: "flex", justifyContent: "right", alignItems: "flex-end",  height: "100%"}}><button className="boton" onClick={() => window.__codePanelGenerate?.()}>Generar Código</button></div>
      <div style={{ width:"29.5%",  height: "100%", display: "flex",  alignItems: "flex-end" }}>
        <h1 className="titulo">CODIGO</h1>

      </div>
    </div>
    <div className="funciones">
      <DiagramCanvas />
      <div className="codigos">
        <CodePanel /> 
      </div>
    </div>
  </div>
  );
}

export default App;