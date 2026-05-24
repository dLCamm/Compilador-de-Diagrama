import { Handle, Position } from "reactflow";

export default function StartEndNode({ data }) {
  const esInicio = data.label === "Inicio";
  const esFin = data.label === "Fin";

  return (
    <div
      style={{
        padding: "15px 30px",
        border: "3px solid var(--border-forma)",
        borderRadius: "50px",
        background: "var(--backr-forma)",
        textAlign: "center",
        color: "var(--border-forma)",
        fontfamily: "Source Code Pro",
        fontstyle: "normal",
        fontWeight: "bold",
        fontFamily: "Source Code Pro, monospace",
        lineheight: "15px",
        fontSize: "18px",


      }}
    >

      {!esInicio && (
        <Handle
          type="target"
          position={Position.Top}
        />
      )}

      {data.label}

      {!esFin && (
        <Handle
          type="source"
          position={Position.Bottom}
        />
      )}

    </div>
  );
}
