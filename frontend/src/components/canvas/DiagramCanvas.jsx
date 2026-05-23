import {ReactFlow, Background,Controls,MiniMap,addEdge,useNodesState,useEdgesState, applyNodeChanges, applyEdgeChanges} from "reactflow";
import { v4 as uuid } from "uuid";
import "reactflow/dist/style.css";
import "./Canvas.css";
import { sanitizeFlow } from "../../utils/sanitizeFlow";

import { useCallback } from "react";

import ProcessNode from "../nodes/ProcessNode";
import ConditionNode from "../nodes/ConditionNode";
import StartEndNode from "../nodes/StartEndNode";
import Toolbar from "../toolbar/Toolbar";
import InputNode from "../nodes/InputNode";
import OutputNode from "../nodes/OutputNode";

const nodeTypes = {
  process: ProcessNode,
  condition: ConditionNode,
  start: StartEndNode,
  end: StartEndNode,
  input: InputNode,
  output: OutputNode
};


export default function DiagramCanvas({nodes,setNodes,edges,setEdges}) {

    const onNodesChange = useCallback(
        (changes) => {

            setNodes((nds) =>
            applyNodeChanges(changes, nds)
            );

        },

        [setNodes]
        );

        const onEdgesChange = useCallback(
        (changes) => {

            setEdges((eds) =>
            applyEdgeChanges(changes, eds)
            );

        },

        [setEdges]
        );

  


    const onConnect = useCallback(
    (params) => {

        const label =
        params.sourceHandle === "true"
            ? "Sí"
            : params.sourceHandle === "false"
            ? "No"
            : "";

        const newEdge = {
        ...params,

        id: uuid(),

        type: "control",

        label
        };

        setEdges((eds) =>
        addEdge(newEdge, eds)
        );
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

    const updateNodeData = (id, newData) => {

        setNodes((nds) =>
            nds.map((node) => {

            if (node.id === id) {

                return {
                ...node,

                data: {
                    ...node.data,
                    ...newData
                }
                };
            }

            return node;
            })
        );
    };

    

    if (type === "process") {
        newNode.data = {
        code: "",
        updateNodeData
        };
    }

    if (type === "condition") {
        newNode.data = {
        expression: "",
        updateNodeData
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

    if (type === "input") {
        newNode.data = {
        variable: "",
        updateNodeData
        };
    }

    if (type === "output") {
        newNode.data = {    
        expression : "",
        updateNodeData
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