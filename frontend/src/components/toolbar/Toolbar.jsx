import "./Toolbar.css";
export default function Toolbar({ addNode }) {

  return (
    <div className="toolbar">

      <button onClick={() => addNode("start")}>
        Inicio
      </button>

      <button onClick={() => addNode("process")}>
        Proceso
      </button>

      <button onClick={() => addNode("condition")}>
        Condición
      </button>

      <button onClick={() => addNode("end")}>
        Fin
      </button>

    </div>
  );
}