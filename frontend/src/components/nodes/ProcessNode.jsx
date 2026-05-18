import { Handle, Position } from "reactflow";

export default function ProcessNode({ data }) {

  return (
    <div
      style={{
        padding: 15,
        border: "2px solid black",
        background: "white",
        minWidth: 120,
        textAlign: "center"
      }}
    >

      <Handle
        type="target"
        position={Position.Top}
      />

      {data.code}

      <Handle
        type="source"
        position={Position.Bottom}
      />

    </div>
  );
}