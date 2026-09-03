import { BarChart3, Library, Search, Waypoints } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { ModeToggle } from "@/components/mode-toggle";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { to: "/crawl", label: "Краулинг", icon: Waypoints },
  { to: "/collections", label: "Коллекции", icon: Library },
  { to: "/search", label: "Поиск", icon: Search },
  { to: "/metrics", label: "Метрики", icon: BarChart3 },
];

export function Layout() {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <aside className="flex w-60 shrink-0 flex-col border-r bg-card">
        <div className="flex h-16 items-center border-b px-5">
          <span className="text-lg font-bold tracking-tight">LanguageProcessing</span>
        </div>
        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-3">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
                  isActive && "bg-accent text-accent-foreground",
                )
              }
            >
              <item.icon className="size-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="flex items-center justify-between border-t px-4 py-3">
          <span className="text-sm text-muted-foreground">Тема</span>
          <ModeToggle />
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto p-6 md:p-8">
        <Outlet />
      </main>
    </div>
  );
}
