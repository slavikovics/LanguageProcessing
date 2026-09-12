import { useEffect, useState } from "react";
import type { Edge, Node, NodeProps } from "reactflow";
import ReactFlow, {
  Background,
  Handle,
  MarkerType,
  Position,
  useEdgesState,
  useNodesState,
} from "reactflow";
import "reactflow/dist/style.css";

import type { SyntaxToken } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { getDepColor, getDepLabel, getPosStyle } from "@/lib/posTags";

function TokenNode({ data }: NodeProps) {
  const style = getPosStyle(data.pos);
  const depColor = getDepColor(data.dep);
  return (
    <div className="flex flex-col items-center gap-1">
      <Handle type="target" position={Position.Top} className="!bg-muted-foreground/50" />
      {data.dep && (
        <span
          className="rounded px-1.5 py-0.5 text-[10px] leading-none whitespace-nowrap"
          style={{ backgroundColor: `${depColor}20`, color: depColor, border: `1px solid ${depColor}` }}
        >
          {getDepLabel(data.dep)}
        </span>
      )}
      <Card className="border-t-4 px-3 py-1.5 shadow-sm" style={{ borderTopColor: style.border }}>
        <div className="flex flex-col items-center gap-1">
          <span className="text-sm font-medium">{data.word}</span>
          <Badge
            variant="outline"
            className="h-4 px-1 py-0 text-[10px]"
            style={{ backgroundColor: style.bg, borderColor: style.border, color: style.text }}
          >
            {data.pos}
          </Badge>
        </div>
      </Card>
      <Handle type="source" position={Position.Bottom} className="!bg-muted-foreground/50" />
    </div>
  );
}

const nodeTypes = { token: TokenNode };

/** Dependency parse tree — tab 2 of the lab. Root at the top, each token's
 * head above it, laid out level-by-level (BFS depth from the sentence
 * root) since spaCy dependency trees aren't necessarily linear left → right. */
export function SyntaxDependencyGraph({
  tokens,
  className = "h-[420px]",
}: {
  tokens: SyntaxToken[];
  className?: string;
}) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    const visible = tokens.filter((tok) => !tok.is_punct);
    if (visible.length === 0) {
      setNodes([]);
      setEdges([]);
      return;
    }

    const byPosition = new Map(visible.map((tok) => [tok.position, tok]));
    const root = visible.find((tok) => tok.head_position === null) ?? visible[0];

    const depth = new Map<number, number>();
    const childrenOf = new Map<number, number[]>();
    for (const tok of visible) {
      if (tok.head_position !== null && byPosition.has(tok.head_position)) {
        const list = childrenOf.get(tok.head_position) ?? [];
        list.push(tok.position);
        childrenOf.set(tok.head_position, list);
      }
    }
    const queue: number[] = [root.position];
    depth.set(root.position, 0);
    while (queue.length > 0) {
      const current = queue.shift() as number;
      for (const child of childrenOf.get(current) ?? []) {
        if (!depth.has(child)) {
          depth.set(child, (depth.get(current) ?? 0) + 1);
          queue.push(child);
        }
      }
    }
    for (const tok of visible) {
      if (!depth.has(tok.position)) depth.set(tok.position, 0);
    }

    const perLevelCount = new Map<number, number>();
    const flowNodes: Node[] = visible.map((tok) => {
      const level = depth.get(tok.position) ?? 0;
      const index = perLevelCount.get(level) ?? 0;
      perLevelCount.set(level, index + 1);
      return {
        id: String(tok.position),
        type: "token",
        position: { x: index * 170, y: level * 130 },
        data: { word: tok.text, pos: tok.pos, dep: tok.head_position !== null ? tok.dep : null },
        draggable: true,
      };
    });

    const flowEdges: Edge[] = visible
      .filter((tok) => tok.head_position !== null && byPosition.has(tok.head_position!))
      .map((tok) => ({
        id: `${tok.head_position}-${tok.position}`,
        source: String(tok.head_position),
        target: String(tok.position),
        type: "straight",
        style: { stroke: getDepColor(tok.dep), strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: getDepColor(tok.dep) },
      }));

    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [tokens, setNodes, setEdges]);

  return (
    <div className={`w-full overflow-hidden rounded-lg border bg-card ${className}`}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.4}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={16} size={1} className="text-border" color="currentColor" />
      </ReactFlow>
    </div>
  );
}
