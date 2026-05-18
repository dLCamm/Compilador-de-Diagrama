import { Handle, Position } from "reactflow";

export default function ConditionNode({ data }) {

  return (
    <div
      style={{
        width: 120,
        height: 120,
        background: "white",
        border: "2px solid black",
        transform: "rotate(45deg)",
        display: "flex",
        justifyContent: "center",
        alignItems: "center"
      }}
    >

      <Handle
        type="target"
        position={Position.Top}
      />

      <Handle
        type="source"
        position={Position.Left}
        id="true"
      />

      <Handle
        type="source"
        position={Position.Right}
        id="false"
      />

      <div
        style={{
          transform: "rotate(-45deg)"
        }}
      >
        {data.expression}
      </div>

    </div>
  );
}