import { Handle, Position } from "reactflow";
import NodeHint from "./NodeHint";

export default function ProcessNode({id, data }) {

  return (
    <div
      style={{
        padding: 15,
        border: "3px solid var(--border-forma)",
        background: "var(--backr-forma)",
        minWidth: 120,
        textAlign: "center",
        color: "var(--border-forma)",
        fontWeight: "bold",
        fontFamily: "Source Code Pro, monospace",
        lineheight: "15px",
        fontSize: "18px",
        borderRadius: "5px",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
       
        
      }}
      className="node-hint-wrap"
    >
      <NodeHint
        titulo="Proceso"
        lineas={[
          "tipo variable = expresion",
          "variable = expresion",
          "variable++",
          "variable--",
          "Tipos: int, float, double, bool, string",
          "Si ya existe la variable, puedes usar solo variable",
        ]}
      />

      <Handle
        type="target"
        position={Position.Top}
      />

      <input
        className="node-field"
        spellCheck="false"

        value={data.code}
        placeholder="Proceso"

        onChange={(e) => {

          data.updateNodeData(id, {
            code: e.target.value
          });

        }}



        style={{
          border: "none",
          outline: "none",
          width: "100%",
          height: "24px",
      
          background: "transparent",
          textAlign: "center",
          color: "var(--border-forma)",
          fontWeight: "bold",
          fontFamily: "Source Code Pro, monospace",
          lineheight: "15px",
          fontSize: "18px",
    
        }}
      />

      <Handle
        type="source"
        position={Position.Bottom}
      />

    </div>
  );
}
