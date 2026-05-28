import {ReactFlow, Background,Controls,MiniMap,addEdge,useNodesState,useEdgesState, applyNodeChanges, applyEdgeChanges, MarkerType} from "reactflow";
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

const nombresFigura = {
  start: "Inicio",
  end: "Fin",
  process: "Proceso",
  condition: "Condicion",
  input: "Entrada",
  output: "Salida",
};

function nombreFigura(node) {
    if (!node) return "figura desconocida";

    const data = node.data || {};

    if (node.type === "process") return data.code || "Proceso";
    if (node.type === "condition") return data.expression || "Condicion";
    if (node.type === "input") return data.variable ? `Entrada ${data.variable}` : "Entrada";
    if (node.type === "output") return data.expression ? `Salida ${data.expression}` : "Salida";

    return data.label || nombresFigura[node.type] || "figura";
}

function nombreConexion(edge, nodes) {
    const source = nodes.find((node) => node.id === edge?.source);
    const target = nodes.find((node) => node.id === edge?.target);
    return `${nombreFigura(source)} y ${nombreFigura(target)}`;
}


export default function DiagramCanvas({nodes,setNodes,edges,setEdges,onEchoEvent}) {

    const onNodesChange = useCallback(
        (changes) => {
            changes
                .filter((change) => change.type === "remove")
                .forEach((change) => {
                    const node = nodes.find((item) => item.id === change.id);
                    onEchoEvent?.(`Se elimino la figura: ${nombreFigura(node)}`);
                });

            setNodes((nds) =>
            applyNodeChanges(changes, nds)
            );

        },

        [nodes, setNodes, onEchoEvent]
        );

        const onEdgesChange = useCallback(
        (changes) => {
            changes
                .filter((change) => change.type === "remove")
                .forEach((change) => {
                    const edge = edges.find((item) => item.id === change.id);
                    onEchoEvent?.(`Se elimino una conexion entre ${nombreConexion(edge, nodes)}`);
                });

            setEdges((eds) =>
            applyEdgeChanges(changes, eds)
            );

        },

        [edges, nodes, setEdges, onEchoEvent]
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

        type: "smoothstep",

        label,

        markerEnd: {
            type: MarkerType.ArrowClosed,
            color: "#486C85"
            

        },

        pathOptions: {
            offset: 30,
            borderRadius: 20,
           
        }
        };

        setEdges((eds) =>
        addEdge(newEdge, eds)
        );
        const source = nodes.find((node) => node.id === params.source);
        const target = nodes.find((node) => node.id === params.target);
        onEchoEvent?.(`Se creo una conexion entre ${nombreFigura(source)} y ${nombreFigura(target)}`);
    },

    [nodes, setEdges, onEchoEvent]
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
    onEchoEvent?.(`Se creo la figura: ${nombreFigura(newNode)}`);
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
                    >

                        <Background />
                        <Controls />
                        <MiniMap
                            style={{
                                width: 130,
                                height: 90
                            }}
                        />

                    </ReactFlow>

                </div>

            </div>
            );
}
