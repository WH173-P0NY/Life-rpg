import type {
  CampaignStudioEdge,
  CampaignStudioNode,
  CampaignValidationReport
} from "../../types/campaigns";

export function validateCampaignLocally(
  nodes: CampaignStudioNode[],
  edges: CampaignStudioEdge[]
): CampaignValidationReport {
  const nodeIds = new Set(nodes.map((node) => node.id));
  const questNodes = nodes.filter((node) => node.nodeKind === "quest");
  const incoming = new Map<string, string[]>();
  const outgoing = new Map<string, string[]>();
  const issues: CampaignValidationReport["issues"] = [];

  nodes.forEach((node) => {
    incoming.set(node.id, []);
    outgoing.set(node.id, []);
  });

  edges.forEach((edge) => {
    if (!nodeIds.has(edge.sourceNodeId) || !nodeIds.has(edge.targetNodeId)) {
      issues.push({
        code: "dangling_edge",
        severity: "error",
        message: "Connection points to a missing node.",
        edgeId: edge.id
      });
      return;
    }
    if (edge.sourceNodeId === edge.targetNodeId) {
      issues.push({
        code: "self_edge",
        severity: "error",
        message: "A node cannot unlock itself.",
        edgeId: edge.id
      });
    }
    outgoing.get(edge.sourceNodeId)?.push(edge.targetNodeId);
    incoming.get(edge.targetNodeId)?.push(edge.sourceNodeId);
  });

  const startingNodes = nodes.filter((node) => (incoming.get(node.id)?.length ?? 0) === 0);
  const finalNodes = nodes.filter((node) => (outgoing.get(node.id)?.length ?? 0) === 0);
  const reachable = new Set<string>();
  const queue = startingNodes.map((node) => node.id);

  while (queue.length) {
    const nodeId = queue.shift();
    if (!nodeId || reachable.has(nodeId)) {
      continue;
    }
    reachable.add(nodeId);
    outgoing.get(nodeId)?.forEach((targetId) => queue.push(targetId));
  }

  nodes.forEach((node) => {
    if (!reachable.has(node.id)) {
      issues.push({
        code: "unreachable_node",
        severity: "error",
        message: "Node is not reachable from a starting point.",
        nodeId: node.id
      });
    }
    if (node.nodeKind === "quest" && !node.title.trim()) {
      issues.push({
        code: "missing_title",
        severity: "error",
        message: "Quest node needs a title.",
        nodeId: node.id
      });
    }
  });

  const hasCycle = detectCycle(nodes, outgoing);

  if (hasCycle) {
    issues.push({
      code: "cycle_detected",
      severity: "error",
      message: "Campaign graph contains a cycle."
    });
  }

  const checks = [
    {
      code: "has_nodes",
      passed: nodes.length > 0,
      label: "Has campaign nodes",
      message: "Add at least one node to the campaign."
    },
    {
      code: "has_quest",
      passed: questNodes.length > 0,
      label: "Has at least one quest",
      message: "Campaign needs at least one quest."
    },
    {
      code: "has_starting_node",
      passed: startingNodes.length > 0,
      label: "Has a starting point",
      message: "At least one node must be available without dependencies."
    },
    {
      code: "has_final_node",
      passed: finalNodes.length > 0,
      label: "Has a final step",
      message: "Campaign should have a final node."
    },
    {
      code: "has_no_cycles",
      passed: !hasCycle,
      label: "Has no cycles",
      message: "Remove circular dependencies."
    },
    {
      code: "all_nodes_reachable",
      passed: nodes.every((node) => reachable.has(node.id)),
      label: "All nodes are reachable",
      message: "Connect isolated nodes to the campaign path."
    }
  ];

  return {
    valid: checks.every((check) => check.passed) && issues.every((issue) => issue.severity !== "error"),
    checks,
    issues
  };
}

function detectCycle(
  nodes: CampaignStudioNode[],
  outgoing: Map<string, string[]>
): boolean {
  const visiting = new Set<string>();
  const visited = new Set<string>();

  function visit(nodeId: string): boolean {
    if (visiting.has(nodeId)) {
      return true;
    }
    if (visited.has(nodeId)) {
      return false;
    }

    visiting.add(nodeId);
    const hasCycle = (outgoing.get(nodeId) ?? []).some(visit);
    visiting.delete(nodeId);
    visited.add(nodeId);
    return hasCycle;
  }

  return nodes.some((node) => visit(node.id));
}
