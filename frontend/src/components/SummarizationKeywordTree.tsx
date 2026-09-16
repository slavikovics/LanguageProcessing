import { useState } from "react";

import type { KeywordGroup } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const DEFAULT_VISIBLE_ROOTS = 15;

function KeywordChildren({ children }: { children: string[] }) {
  if (children.length === 0) return null;
  return (
    <ul className="ml-2.5 flex flex-col border-l border-border">
      {children.map((child) => (
        <li key={child} className="relative flex items-center py-1 pl-4">
          <span className="absolute top-1/2 left-0 h-px w-3.5 bg-border" />
          <Badge variant="outline" className="min-w-0 font-normal break-words whitespace-normal">
            {child}
          </Badge>
        </li>
      ))}
    </ul>
  );
}

export function SummarizationKeywordTree({ groups }: { groups: KeywordGroup[] }) {
  const [expanded, setExpanded] = useState(false);

  if (groups.length === 0) return null;

  const visible = expanded ? groups : groups.slice(0, DEFAULT_VISIBLE_ROOTS);
  const hiddenCount = groups.length - visible.length;

  return (
    <div className="flex flex-col gap-2">
      <ul className="flex flex-col gap-1.5">
        {visible.map((group) => (
          <li key={group.term} className="flex flex-col">
            <Badge variant="secondary" className="w-fit min-w-0 break-words whitespace-normal">
              {group.term}
            </Badge>
            <KeywordChildren children={group.children} />
          </li>
        ))}
      </ul>

      {hiddenCount > 0 && (
        <Button type="button" variant="ghost" size="sm" className="w-fit" onClick={() => setExpanded(true)}>
          Показать ещё {hiddenCount}
        </Button>
      )}
      {expanded && groups.length > DEFAULT_VISIBLE_ROOTS && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="w-fit"
          onClick={() => setExpanded(false)}
        >
          Свернуть
        </Button>
      )}
    </div>
  );
}
