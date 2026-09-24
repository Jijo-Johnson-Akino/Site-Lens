export type LayoutInput = {
  id: string;
  depth: number | null;
  inbound: number;
  url: string;
};

export const NODE_WIDTH = 232;
export const NODE_HEIGHT = 118;
const H_GAP = 40;
const V_GAP = 78;

export function hierarchicalLayout(nodes: LayoutInput[]): Record<string, { x: number; y: number }> {
  const groups = new Map<number, LayoutInput[]>();
  const unknown: LayoutInput[] = [];
  for (const node of nodes) {
    if (typeof node.depth !== "number") {
      unknown.push(node);
      continue;
    }
    const row = groups.get(node.depth) ?? [];
    row.push(node);
    groups.set(node.depth, row);
  }
  const depths = [...groups.keys()].sort((left, right) => left - right);
  if (unknown.length) {
    depths.push(Number.MAX_SAFE_INTEGER);
  }
  const positions: Record<string, { x: number; y: number }> = {};
  depths.forEach((depth, row) => {
    const rowNodes = (depth === Number.MAX_SAFE_INTEGER ? unknown : groups.get(depth) || []).slice().sort((left, right) => {
      if (right.inbound !== left.inbound) {
        return right.inbound - left.inbound;
      }
      return left.url.localeCompare(right.url);
    });
    const y = row * (NODE_HEIGHT + V_GAP);
    rowNodes.forEach((node, index) => {
      positions[node.id] = { x: index * (NODE_WIDTH + H_GAP), y };
    });
  });
  return positions;
}
