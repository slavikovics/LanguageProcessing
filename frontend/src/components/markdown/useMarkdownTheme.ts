import { useTheme } from "@/components/theme-provider";

export function useMarkdownTheme(themeOverride?: "light" | "dark"): "light" | "dark" {
  const { theme } = useTheme();
  return themeOverride ?? theme;
}
