"use client";

import { useEffect, useMemo } from "react";
import {
  Background,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type { ArchitectureEdge, ArchitectureNode } from "@/lib/scan/api";
import { hierarchicalLayout, NODE_HEIGHT, NODE_WIDTH } from "@/lib/scan/architecture-layout";
import { crawlDepthLabel, nodeHeading, nodeTone } from "@/lib/scan/architecture-ui";
import { cn } from "@/lib/utils";

type GraphNodeData = {
  node: ArchitectureNode;
};

function ArchitecturePageNode({ data, selected }: NodeProps<Node<GraphNodeData>>) {
  const node = data.node;
  const tone = nodeTone(node);
  return (
    <div
      className={cn(
        "rounded-xl border bg-card px-3 py-2 text-left shadow-sm",
        selected && "ring-2 ring-ring",
        tone === "failed" && "border-critical/40 bg-muted/70 text-muted-foreground",
        tone === "critical" && "border-critical",
        tone === "warn" && "border-warn",
        tone === "orphan" && "border-warn/70",
        tone === "default" && "border-border",
      )}
      style={{ width: NODE_WIDTH - 12 }}
    >
      <Handle type="target" position={Position.Top} className="!h-2 !w-2 !bg-muted-foreground/40" />
      <p className="truncate text-sm font-medium text-foreground">{nodeHeading(node)}</p>
      <p className="mt-0.5 truncate font-mono text-[11px] text-muted-foreground">{node.path}</p>
      <p className="mt-1 text-[11px] text-muted-foreground">
        {node.page_type_label || node.page_type || "Unknown"} · {crawlDepthLabel(node.depth)}
      </p>
      <p className="mt-1 font-mono text-[11px] text-muted-foreground">
        ← {node.inbound_link_count} · → {node.outbound_link_count} · Issues {node.issue_count}
      </p>
      <Handle type="source" position={Position.Bottom} className="!h-2 !w-2 !bg-muted-foreground/40" />
    </div>
  );
}

const nodeTypes = { architecture: ArchitecturePageNode };

function FocusSelected({ selectedId }: { selectedId: string | null }) {
  const { fitView } = useReactFlow();
  useEffect(() => {
    if (!selectedId) {
      return;
    }
    void fitView({ nodes: [{ id: selectedId }], padding: 1.1, duration: 280 });
  }, [selectedId, fitView]);
  return null;
}

function GraphCanvas({
  nodes,
  edges,
  selectedId,
  onSelect,
}: {
  nodes: ArchitectureNode[];
  edges: ArchitectureEdge[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const { fitView, zoomIn, zoomOut } = useReactFlow();
  const layout = useMemo(
    () =>
      hierarchicalLayout(
        nodes.map((node) => ({
          id: node.id,
          depth: typeof node.depth === "number" ? node.depth : null,
          inbound: node.inbound_link_count,
          url: node.normalized_url || node.url,
        })),
      ),
    [nodes],
  );
  const flowNodes: Node<GraphNodeData>[] = useMemo(
    () =>
      nodes.map((node) => ({
        id: node.id,
        type: "architecture",
        position: layout[node.id] || { x: 0, y: 0 },
        data: { node },
        selected: node.id === selectedId,
        style: { width: NODE_WIDTH, height: NODE_HEIGHT },
        draggable: false,
      })),
    [layout, nodes, selectedId],
  );
  const flowEdges: Edge[] = useMemo(
    () =>
      edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        style: { stroke: "var(--border)", strokeWidth: Math.min(2.5, 1 + (edge.link_count - 1) * 0.25) },
      })),
    [edges],
  );

  return (
    <div className="relative h-[560px] w-full overflow-hidden rounded-xl border border-border bg-muted/20">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => onSelect(node.id)}
        fitView
        minZoom={0.2}
        maxZoom={1.6}
        nodesConnectable={false}
        nodesDraggable={false}
        elementsSelectable
        proOptions={{ hideAttribution: true }}
        aria-label="Website architecture graph"
      >
        <Background gap={18} size={1} color="var(--border)" />
        <MiniMap
          className="!hidden lg:!block"
          pannable
          zoomable
          maskColor="color-mix(in oklab, var(--navy) 18%, transparent)"
          nodeColor="var(--muted)"
        />
        <FocusSelected selectedId={selectedId} />
      </ReactFlow>
      <div className="absolute top-3 right-3 z-10 flex gap-2">
        <button type="button" className="rounded-lg border border-border bg-card px-2 py-1 text-xs" onClick={() => void zoomIn()}>
          Zoom in
        </button>
        <button type="button" className="rounded-lg border border-border bg-card px-2 py-1 text-xs" onClick={() => void zoomOut()}>
          Zoom out
        </button>
        <button type="button" className="rounded-lg border border-border bg-card px-2 py-1 text-xs" onClick={() => void fitView({ padding: 0.2, duration: 200 })}>
          Fit to screen
        </button>
      </div>
    </div>
  );
}

export function ArchitectureGraph({
  nodes,
  edges,
  selectedId,
  onSelect,
}: {
  nodes: ArchitectureNode[];
  edges: ArchitectureEdge[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <ReactFlowProvider>
      <GraphCanvas nodes={nodes} edges={edges} selectedId={selectedId} onSelect={onSelect} />
    </ReactFlowProvider>
  );
}
