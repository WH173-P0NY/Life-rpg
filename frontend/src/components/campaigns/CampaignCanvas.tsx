import { useCallback, useEffect, useMemo } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type Node,
  type OnNodeDrag
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { useI18n } from "../../i18n";
import type {
  CampaignStudioEdge,
  CampaignStudioMode,
  CampaignStudioNode
} from "../../types/campaigns";
import { CampaignNode } from "./CampaignNode";
import {
  toFlowEdges,
  toFlowNodes,
  type CampaignFlowEdge,
  type CampaignFlowNode
} from "./campaignFlowMapper";

interface CampaignCanvasProps {
  nodes: CampaignStudioNode[];
  edges: CampaignStudioEdge[];
  mode: CampaignStudioMode;
  onNodeSelect: (nodeId: string | null) => void;
  onEdgeSelect: (edgeId: string | null) => void;
  onConnect: (sourceNodeId: string, targetNodeId: string) => Promise<void>;
  onNodeDragStop: (nodeId: string, position: { x: number; y: number }) => Promise<void>;
  onNodesDelete: (nodeIds: string[]) => Promise<void>;
  onEdgesDelete: (edgeIds: string[]) => Promise<void>;
}

const nodeTypes = {
  campaignNode: CampaignNode
};

export function CampaignCanvas(props: CampaignCanvasProps) {
  return (
    <ReactFlowProvider>
      <CampaignCanvasInner {...props} />
    </ReactFlowProvider>
  );
}

function CampaignCanvasInner({
  nodes,
  edges,
  mode,
  onNodeSelect,
  onEdgeSelect,
  onConnect,
  onNodeDragStop,
  onNodesDelete,
  onEdgesDelete
}: CampaignCanvasProps) {
  const { t } = useI18n();
  const initialNodes = useMemo(() => toFlowNodes(nodes, mode, t), [mode, nodes, t]);
  const initialEdges = useMemo(() => toFlowEdges(edges), [edges]);
  const [flowNodes, setNodes, handleNodesChange] =
    useNodesState<CampaignFlowNode>(initialNodes);
  const [flowEdges, setEdges, handleEdgesChange] =
    useEdgesState<CampaignFlowEdge>(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
  }, [initialNodes, setNodes]);

  useEffect(() => {
    setEdges(initialEdges);
  }, [initialEdges, setEdges]);

  const handleConnect = useCallback(
    (connection: Connection) => {
      if (mode !== "builder" || !connection.source || !connection.target) {
        return;
      }
      if (connection.source === connection.target) {
        return;
      }
      void onConnect(connection.source, connection.target);
    },
    [mode, onConnect]
  );

  const handleNodeDragStop = useCallback<OnNodeDrag<CampaignFlowNode>>(
    (_event, node) => {
      if (mode !== "builder") {
        return;
      }
      void onNodeDragStop(node.id, node.position);
    },
    [mode, onNodeDragStop]
  );

  const handleNodesDelete = useCallback(
    (deletedNodes: Node[]) => {
      if (mode !== "builder") {
        return;
      }
      void onNodesDelete(deletedNodes.map((node) => node.id));
    },
    [mode, onNodesDelete]
  );

  const handleEdgesDelete = useCallback(
    (deletedEdges: Edge[]) => {
      if (mode !== "builder") {
        return;
      }
      void onEdgesDelete(deletedEdges.map((edge) => edge.id));
    },
    [mode, onEdgesDelete]
  );

  return (
    <div className="h-[680px] min-h-[520px] overflow-hidden rounded-lg border border-white/10 bg-black/25">
      <ReactFlow
        colorMode="dark"
        deleteKeyCode={mode === "builder" ? ["Backspace", "Delete"] : null}
        edges={flowEdges}
        fitView
        fitViewOptions={{ padding: 0.24 }}
        maxZoom={1.4}
        minZoom={0.3}
        nodeTypes={nodeTypes}
        nodes={flowNodes}
        nodesConnectable={mode === "builder"}
        nodesDraggable={mode === "builder"}
        onConnect={handleConnect}
        onEdgesChange={handleEdgesChange}
        onEdgesDelete={handleEdgesDelete}
        onNodeClick={(_event, node) => {
          onNodeSelect(node.id);
          onEdgeSelect(null);
        }}
        onNodeDragStop={handleNodeDragStop}
        onNodesChange={handleNodesChange}
        onNodesDelete={handleNodesDelete}
        onPaneClick={() => {
          onNodeSelect(null);
          onEdgeSelect(null);
        }}
        onEdgeClick={(_event, edge) => {
          onEdgeSelect(edge.id);
          onNodeSelect(null);
        }}
        panOnScroll
        proOptions={{ hideAttribution: true }}
      >
        <Background color="rgb(var(--color-border))" gap={28} size={1} />
        <Controls
          className="!border !border-white/10 !bg-zinc-950/80 !shadow-premium"
          position="bottom-left"
        />
        <MiniMap
          className="!border !border-white/10 !bg-zinc-950/80"
          maskColor="rgb(0 0 0 / 0.45)"
          nodeColor={(node) => {
            const data = node.data as CampaignFlowNode["data"];
            if (data.node.state === "completed") {
              return "rgb(var(--color-success))";
            }
            if (data.node.state === "available") {
              return "rgb(var(--color-xp))";
            }
            return "rgb(82 82 91)";
          }}
          pannable
          position="bottom-right"
          zoomable
        />
      </ReactFlow>
    </div>
  );
}
