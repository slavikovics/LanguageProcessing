import type { KeywordGroup } from "@/api/types";
import { Badge } from "@/components/ui/badge";

export function SummarizationKeywordTree({ groups }: { groups: KeywordGroup[] }) {
  if (groups.length === 0) return null;

  return (
    <ul className="flex flex-col items-center gap-3">
      {groups.map((group) => (
        <li key={group.term} className="flex flex-col items-center gap-1.5">
          <Badge variant="secondary">{group.term}</Badge>
          {group.children.length > 0 && (
            <ul className="flex flex-wrap items-center justify-center gap-1.5">
              {group.children.map((child) => (
                <li key={child}>
                  <Badge variant="outline" className="font-normal">
                    {child}
                  </Badge>
                </li>
              ))}
            </ul>
          )}
        </li>
      ))}
    </ul>
  );
}
