import { Handle, Position } from "reactflow";

export default function ConditionNode({id, data }) {

  return (
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
        fontWeight: "bold",
        fontFamily: "Source Code Pro, monospace",
        lineheight: "15px",
        fontSize: "18px",
        borderRadius: "5px",
      }}
    >

      <Handle
        type="target"
        position={Position.Top}
      />

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
      rows={1}

        value={data.expression}

        onChange={(e) => {

          data.updateNodeData(id, {
            expression: e.target.value
          });

        }}



        style={{
          border: "none",
          outline: "none",
          resize: "none",
          width: "100%",
          height: "auto",
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
  );
}