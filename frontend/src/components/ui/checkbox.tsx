import * as React from "react"
import { Checkbox as CheckboxPrimitive } from "radix-ui"
import { CheckIcon } from "lucide-react"

import { cn } from "@/lib/utils"

function Checkbox({
  className,
  size = "default",
  ...props
}: React.ComponentProps<typeof CheckboxPrimitive.Root> & {
  size?: "default" | "lg"
}) {
  return (
    <CheckboxPrimitive.Root
      data-slot="checkbox"
      data-size={size}
      className={cn(
        "peer group/checkbox border-input dark:bg-input/30 data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground dark:data-[state=checked]:bg-primary data-[state=checked]:border-primary focus-visible:border-ring focus-visible:ring-ring/50 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive shrink-0 rounded-[4px] border shadow-xs transition-shadow outline-none focus-visible:ring-[3px] disabled:cursor-not-allowed disabled:opacity-50 data-[size=default]:size-4 data-[size=lg]:size-9 data-[size=lg]:rounded-md",
        className
      )}
      {...props}
    >
      <CheckboxPrimitive.Indicator
        data-slot="checkbox-indicator"
        className="flex items-center justify-center text-current transition-none"
      >
        <CheckIcon className="size-3.5 group-data-[size=lg]/checkbox:size-5" />
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  )
}

export { Checkbox }
