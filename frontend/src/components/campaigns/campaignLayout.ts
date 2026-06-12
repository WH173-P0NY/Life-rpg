import type {
  CampaignStudioEdge,
  CampaignStudioNode,
  CampaignNodePositionPayload
} from "../../types/campaigns";

const nodeWidth = 236;
const nodeHeight = 136;
const horizontalGap = 88;
const verticalGap = 56;
const horizontalSpacing = nodeWidth + horizontalGap;
const verticalSpacing = nodeHeight + verticalGap;
const startX = 160;
const startY = 120;
const legacyMaxX = 120;
const legacyMaxY = 100;
const gridSize = 12;
const maxCollisionPasses = 500;

type RawPosition = Pick<CampaignNodePositionPayload, "x" | "y">;

export function layoutCampaignNodes(
  nodes: CampaignStudioNode[],
  edges: CampaignStudioEdge[]
): CampaignNodePositionPayload[] {
  if (!nodes.length) {
    return [];
  }

  const nodeIds = new Set(nodes.map((node) => node.id));
  const incomingCount = new Map<string, number>();
  const outgoing = new Map<string, string[]>();

  nodes.forEach((node) => {
    incomingCount.set(node.id, 0);
    outgoing.set(node.id, []);
  });

  edges.forEach((edge) => {
    if (!nodeIds.has(edge.sourceNodeId) || !nodeIds.has(edge.targetNodeId)) {
      return;
    }
    outgoing.get(edge.sourceNodeId)?.push(edge.targetNodeId);
    incomingCount.set(edge.targetNodeId, (incomingCount.get(edge.targetNodeId) ?? 0) + 1);
  });

  const queue = nodes
    .filter((node) => (incomingCount.get(node.id) ?? 0) === 0)
    .map((node) => node.id);
  const rank = new Map<string, number>();

  queue.forEach((nodeId) => rank.set(nodeId, 0));

  while (queue.length) {
    const nodeId = queue.shift();
    if (!nodeId) {
      continue;
    }
    const nextRank = (rank.get(nodeId) ?? 0) + 1;
    outgoing.get(nodeId)?.forEach((targetId) => {
      incomingCount.set(targetId, (incomingCount.get(targetId) ?? 1) - 1);
      rank.set(targetId, Math.max(rank.get(targetId) ?? 0, nextRank));
      if ((incomingCount.get(targetId) ?? 0) <= 0) {
        queue.push(targetId);
      }
    });
  }

  nodes.forEach((node, index) => {
    if (!rank.has(node.id)) {
      rank.set(node.id, Math.floor(index / 4));
    }
  });

  const layers = new Map<number, CampaignStudioNode[]>();
  nodes.forEach((node) => {
    const nodeRank = rank.get(node.id) ?? 0;
    layers.set(nodeRank, [...(layers.get(nodeRank) ?? []), node]);
  });

  const positions: CampaignNodePositionPayload[] = [];
  Array.from(layers.entries())
    .sort(([leftRank], [rightRank]) => leftRank - rightRank)
    .forEach(([nodeRank, layerNodes]) => {
      layerNodes.forEach((node, index) => {
        positions.push({
          nodeId: node.id,
          x: startX + nodeRank * horizontalSpacing,
          y: startY + index * verticalSpacing
        });
      });
    });

  return resolveCampaignNodeCollisions(positions);
}

export function getCampaignNodePosition(
  node: CampaignStudioNode
): CampaignNodePositionPayload {
  return {
    nodeId: node.id,
    x: node.position.x,
    y: node.position.y
  };
}

export function normalizeCampaignNodePositions(
  positions: CampaignNodePositionPayload[]
): CampaignNodePositionPayload[] {
  const shouldScaleLegacy = isLegacyCoordinateSet(positions);

  return positions.map((position) => {
    const normalized = normalizeCampaignCoordinates(position, shouldScaleLegacy);

    return {
      nodeId: position.nodeId,
      ...normalized
    };
  });
}

export function resolveCampaignNodeCollisions(
  positions: CampaignNodePositionPayload[]
): CampaignNodePositionPayload[] {
  const placed: CampaignNodePositionPayload[] = [];

  normalizeCampaignNodePositions(positions).forEach((position) => {
    let candidate = {
      ...position,
      x: snapX(position.x),
      y: snapY(position.y)
    };

    for (let pass = 0; pass < maxCollisionPasses; pass += 1) {
      const blocker = placed.find((existing) => intersects(candidate, existing));

      if (!blocker) {
        placed.push(candidate);
        return;
      }

      candidate = {
        ...candidate,
        y: snapY(blocker.y + verticalSpacing)
      };
    }

    placed.push({
      ...candidate,
      x: snapX(candidate.x + horizontalSpacing),
      y: startY
    });
  });

  return placed;
}

export function findOpenCampaignNodePosition(
  nodes: CampaignStudioNode[],
  preferredPosition?: RawPosition
): RawPosition {
  const existingPositions = nodes.map(getCampaignNodePosition);
  const normalizedExisting = resolveCampaignNodeCollisions(existingPositions);
  const fallbackPosition = normalizedExisting.length
    ? {
        x: Math.max(...normalizedExisting.map((position) => position.x)) + horizontalSpacing,
        y: startY
      }
    : {
        x: startX,
        y: startY
      };
  const candidateId = "__new_campaign_node__";
  const resolved = resolveCampaignNodeCollisions([
    ...normalizedExisting,
    {
      nodeId: candidateId,
      ...(preferredPosition ?? fallbackPosition)
    }
  ]);
  const candidate = resolved.find((position) => position.nodeId === candidateId);

  return {
    x: candidate?.x ?? fallbackPosition.x,
    y: candidate?.y ?? fallbackPosition.y
  };
}

export function resolveCampaignNodeDragPositions(
  nodes: CampaignStudioNode[],
  draggedNodeId: string,
  draggedPosition: RawPosition
): CampaignNodePositionPayload[] {
  const existingPositions = nodes
    .filter((node) => node.id !== draggedNodeId)
    .map(getCampaignNodePosition);
  const normalizedExisting = resolveCampaignNodeCollisions(existingPositions);

  return resolveCampaignNodeCollisions([
    ...normalizedExisting,
    {
      nodeId: draggedNodeId,
      x: draggedPosition.x,
      y: draggedPosition.y
    }
  ]);
}

function isLegacyCoordinateSet(positions: CampaignNodePositionPayload[]): boolean {
  if (!positions.length) {
    return false;
  }

  return positions.every(
    (position) =>
      position.x >= 0 &&
      position.y >= 0 &&
      position.x <= legacyMaxX &&
      position.y <= legacyMaxY
  );
}

function normalizeCampaignCoordinates(
  position: RawPosition,
  shouldScaleLegacy: boolean
): RawPosition {
  if (!shouldScaleLegacy) {
    return {
      x: Math.max(startX, position.x),
      y: Math.max(startY, position.y)
    };
  }

  return {
    x: startX + position.x * (horizontalSpacing / 10),
    y: startY + position.y * (verticalSpacing / 10)
  };
}

function intersects(
  left: CampaignNodePositionPayload,
  right: CampaignNodePositionPayload
): boolean {
  return (
    Math.abs(left.x - right.x) < horizontalSpacing &&
    Math.abs(left.y - right.y) < verticalSpacing
  );
}

function snapX(value: number): number {
  return Math.max(startX, Math.round(value / gridSize) * gridSize);
}

function snapY(value: number): number {
  return Math.max(startY, Math.round(value / gridSize) * gridSize);
}
