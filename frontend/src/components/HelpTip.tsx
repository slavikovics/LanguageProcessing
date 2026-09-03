import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

export function HelpTip({ text }: { text: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          tabIndex={0}
          aria-label={text}
          className="inline-flex h-[1.1rem] w-[1.1rem] cursor-help items-center justify-center rounded-full bg-muted text-[0.65rem] font-medium text-muted-foreground"
        >
          ?
        </span>
      </TooltipTrigger>
      <TooltipContent>{text}</TooltipContent>
    </Tooltip>
  );
}
