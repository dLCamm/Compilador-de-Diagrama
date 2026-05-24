import { Handle, Position } from "reactflow";
import NodeHint from "./NodeHint";

export default function ConditionNode({id, data }) {

  return (
    <div
      style={{
        width: 170,
        height: 170,
        position: "relative",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
      }}
      className="node-hint-wrap"
    >
      <NodeHint
        titulo="Condicion"
        lineas={[
          "expresion operador expresion",
          "Operadores: >, <, >=, <=, ==, !=",
        ]}
      />

      <Handle
        type="target"
        position={Position.Top}
        style={{
          top: 1,
          left: "50%",
          transform: "translate(-50%, -50%)",
          zIndex: 10
        }}
      />

      <div
        style={{
          width: 120,
          height: 120,
          background: "var(--backr-forma)",
          border: "3px solid var(--border-forma)",
          color: "var(--border-forma)",
          fontWeight: "bold",
          transform: "rotate(45deg)",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          fontfamily: "Source Code Pro",
          fontstyle: "normal",
          fontFamily: "Source Code Pro, monospace",
          lineheight: "15px",
          fontSize: "18px",
          borderRadius: "5px",
        }}
      >
        <Handle
          type="source"
          position={Position.Bottom}
          id="true"
        />

        <Handle
          type="source"
          position={Position.Right}
          id="false"
        />

        <textarea
          className="node-field"
        rows={1}

          value={data.expression}
          placeholder="Condición"

          onChange={(e) => {

            data.updateNodeData(id, {
              expression: e.target.value
            });

          }}



          style={{
            border: "none",
            outline: "none",
            resize: "none",
            overflow: "hidden",
            width: "100%",
            height: "24px",
            transform: "rotate(-45deg)",
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
      </div>
      

    </div>
  );
}
