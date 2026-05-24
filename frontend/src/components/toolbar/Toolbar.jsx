import "./Toolbar.css";
export default function Toolbar({ addNode }) {

  return (
    <div className="toolbar">

      <button className="button_inicio_fin" onClick={() => addNode("start")}>
        Inicio
      </button>

      <button className="button_inicio_fin" onClick={() => addNode("end")}>
        Fin
      </button>

      <button className="button_proceso" onClick={() => addNode("process")}>
        Proceso
      </button>

      <button className="button_condicion" onClick={() => addNode("condition")}>
        <div className="condition_diamond">
          <div className="condition_text">
            Condición
          </div>
        </div>
      </button>

      <button className="button_entrada_salida" onClick={() => addNode("input")}>
        <div style={{ transform: "skewX(20deg)" }}>
          Entrada
        </div>
      </button>

      <button className="button_entrada_salida" onClick={() => addNode("output")}>
        <div style={{ transform: "skewX(20deg)" }}>
          Salida
        </div>
      </button>

    </div>
  );
}
