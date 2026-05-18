import {ReactFlow, Background,Controls,MiniMap,addEdge,useNodesState,useEdgesState} from "reactflow";
import { v4 as uuid } from "uuid";
import "reactflow/dist/style.css";
import "./Canvas.css";

import { useCallback } from "react";

import ProcessNode from "../nodes/ProcessNode";
import ConditionNode from "../nodes/ConditionNode";
import StartEndNode from "../nodes/StartEndNode";
import Toolbar from "../toolbar/Toolbar";

const nodeTypes = {
  process: ProcessNode,
  condition: ConditionNode,
  start: StartEndNode,
  end: StartEndNode
};


export default function DiagramCanvas() {

  const [nodes, setNodes, onNodesChange] =
    useNodesState([]);

  const [edges, setEdges, onEdgesChange] =
    useEdgesState([]);

  const onConnect = useCallback(
    (params) => {
        setEdges((eds) => addEdge(params, eds));
    },
    [setEdges]
);
  const addNode = (type) => {

    const newNode = {
        id: uuid(),

        type,

        position: {
        x: Math.random() * 400,
        y: Math.random() * 400
        },

        data: {}
    };

    

    if (type === "process") {
        newNode.data = {
        code: "nuevo proceso"
        };
    }

    if (type === "condition") {
        newNode.data = {
        expression: "x > 0"
        };
    }

    if (type === "start") {
        newNode.data = {
        label: "Inicio"
        };
    }

    if (type === "end") {
        newNode.data = {
        label: "Fin"
        };
    }

    setNodes((nds) => [...nds, newNode]);
    };

  return (

            <div
                className="DiagramCanvas"
            >

                <Toolbar addNode={addNode} />

                <div style={{ flex: 1, backgroundColor: "var(--pizzarra)", width: "65%", borderRadius: "8px" }}>

                    <ReactFlow
                        nodes={nodes}
                        edges={edges}
                        onNodesChange={onNodesChange}
                        onEdgesChange={onEdgesChange}
                        onConnect={onConnect}
                        nodeTypes={nodeTypes}
                        fitView
                    >

                        <Background />
                        <Controls />
                        <MiniMap />

                    </ReactFlow>

                </div>

            </div>
            );
}