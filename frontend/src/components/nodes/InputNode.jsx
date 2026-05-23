import { Handle, Position } from "reactflow";

export default function InputNode({ id, data }) {

    return (

        <div
            style={{
                width: "200px",
                height: "60px",
                backgroundColor: "var(--backr-forma)",
                border: "3px solid var(--border-forma)",
                transform: "skewX(-20deg)",
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                position: "relative"
            }}
        >

            <Handle
                type="target"
                position={Position.Top}
            />

            <input

                value={data.variable}

                onChange={(e) => {

                    data.updateNodeData(id, {
                        variable: e.target.value
                    });

                }}

                placeholder="Entrada"

                style={{

                    width: "80%",
                    background: "transparent",
                    border: "none",
                    outline: "none",
                    boxShadow: "none",
                    color: "var(--border-forma)",
                    textAlign: "center",
                    fontFamily: "Source Code Pro, monospace",
                    fontWeight: "bold",
                    fontSize: "18px",
                    lineHeight: "15px",
                    transform: "skewX(20deg)",
                    appearance: "none",
                    WebkitAppearance: "none",
                    MozAppearance: "none"
                }}
            />

            <Handle
                type="source"
                position={Position.Bottom}
            />

        </div>
    );
}