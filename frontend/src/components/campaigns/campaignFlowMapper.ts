import type { Edge, Node } from "@xyflow/react";

import type {
  CampaignStudioEdge,
  CampaignStudioMode,
  CampaignStudioNode
} from "../../types/campaigns";
import type { TranslationKey } from "../../i18n";
import {
  getCampaignNodePosition,
  resolveCampaignNodeCollisions
} from "./campaignLayout";

export interface CampaignFlowNodeData extends Record<string, unknown> {
  node: CampaignStudioNode;
  mode: CampaignStudioMode;
  t: (key: TranslationKey) => string;
}

export type CampaignFlowNode = Node<CampaignFlowNodeData, "campaignNode">;
export type CampaignFlowEdge = Edge<{ edge: CampaignStudioEdge }>;

export function toFlowNodes(
  nodes: CampaignStudioNode[],
  mode: CampaignStudioMode,
  t: (key: TranslationKey) => string
): CampaignFlowNode[] {
  const positions = new Map(
    resolveCampaignNodeCollisions(nodes.map(getCampaignNodePosition)).map((position) => [
      position.nodeId,
      {
        x: position.x,
        y: position.y
      }
    ])
  );

  return nodes.map((node) => ({
    id: node.id,
    type: "campaignNode",
    position: positions.get(node.id) ?? node.position,
    data: {
      node,
      mode,
      t
    },
    draggable: mode === "builder",
    selectable: true
  }));
}

export function toFlowEdges(edges: CampaignStudioEdge[]): CampaignFlowEdge[] {
  return edges.map((edge) => ({
    id: edge.id,
    source: edge.sourceNodeId,
    target: edge.targetNodeId,
    type: "smoothstep",
    animated: false,
    data: { edge },
    style: {
      stroke: "rgb(var(--color-xp) / 0.45)",
      strokeWidth: 2
    }
  }));
}
