import { Moon, Sun } from "lucide-react";

import { Switch } from "@/components/ui/switch";
import { useTheme } from "@/components/theme-provider";

export function ModeToggle() {
  const { theme, setTheme } = useTheme();
  const isDark = theme === "dark";

  return (
    <div className="flex items-center gap-2">
      <Sun className="size-4 text-muted-foreground" />
      <Switch
        checked={isDark}
        onCheckedChange={(checked) => setTheme(checked ? "dark" : "light")}
        aria-label="Переключить тему"
      />
      <Moon className="size-4 text-muted-foreground" />
    </div>
  );
}
