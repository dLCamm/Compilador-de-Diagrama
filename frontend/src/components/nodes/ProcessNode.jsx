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
        ]}
      />

      <Handle
        type="target"
        position={Position.Top}
      />

      <textarea
        className="node-field"
      rows={1}

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
          resize: "none",
          width: "100%",
      
          background: "transparent",
          textAlign: "center",
          color: "var(--border-forma)",
          fontWeight: "bold",
          fontFamily: "Source Code Pro, monospace",
          lineheight: "15px",
          fontSize: "18px",
          spellcheck: "false",
    
        }}
      />

      <Handle
        type="source"
        position={Position.Bottom}
      />

    </div>
  );
}
