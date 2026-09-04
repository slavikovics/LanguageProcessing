import { BarChart3, HelpCircle, Library, Search, Waypoints } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { CollectionSwitcher } from "@/components/CollectionSwitcher";
import { ModeToggle } from "@/components/mode-toggle";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { to: "/crawl", label: "Краулинг", icon: Waypoints },
  { to: "/collections", label: "Коллекции", icon: Library },
  { to: "/search", label: "Поиск", icon: Search },
  { to: "/metrics", label: "Метрики", icon: BarChart3 },
  { to: "/help", label: "Справка", icon: HelpCircle },
];

export function Layout() {
  return (
    <div className="h-screen overflow-hidden bg-background">
      <header className="pointer-events-none fixed inset-x-0 top-0 z-40 flex justify-center px-4 py-3">
        <div className="pointer-events-auto flex max-w-full items-center gap-1 overflow-x-auto rounded-xl border bg-card/90 p-1.5 pt-2 shadow-lg backdrop-blur-md">
          <nav className="flex shrink-0 items-center gap-1">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-all duration-150 hover:-translate-y-0.5 hover:bg-accent hover:text-accent-foreground active:scale-[0.97] active:translate-y-0",
                    isActive && "bg-accent text-accent-foreground",
                  )
                }
              >
                <item.icon className="size-4 transition-transform duration-150" />
                {item.label}
              </NavLink>
            ))}
          </nav>
          <Separator orientation="vertical" className="h-6 shrink-0" />
          <div className="shrink-0 px-1">
            <ModeToggle />
          </div>
          <div className="shrink-0">
            <CollectionSwitcher />
          </div>
        </div>
      </header>
      <ScrollArea className="h-full">
        <main className="mx-auto w-full max-w-6xl px-6 pt-24 pb-6 md:px-8 md:pt-28 md:pb-8">
          <Outlet />
        </main>
      </ScrollArea>
    </div>
  );
}
