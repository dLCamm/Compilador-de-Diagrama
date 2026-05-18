import { Handle, Position } from "reactflow";

export default function StartEndNode({ data }) {

  return (
    <div
      style={{
        padding: "15px 30px",
        border: "2px solid black",
        borderRadius: "50px",
        background: "white",
        textAlign: "center"
      }}
    >

      <Handle
        type="target"
        position={Position.Top}
      />

      {data.label}

      <Handle
        type="source"
        position={Position.Bottom}
      />

    </div>
  );
}