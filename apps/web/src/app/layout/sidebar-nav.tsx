import { NavLink } from "react-router-dom";
import { navGroups, type NavItem } from "@/app/layout/nav-config";
import { NavIcon } from "@/app/layout/nav-icons";

function itemClassName(isActive: boolean, collapsed: boolean) {
  return [
    "relative flex h-9 items-center gap-3 rounded-sm text-sm transition-colors duration-instant ease-brand-out",
    collapsed ? "justify-center px-0" : "px-3",
    isActive
      ? "bg-turquoise-100 font-medium text-turquoise-900 before:absolute before:inset-y-1 before:left-0 before:w-[3px] before:rounded-sm before:bg-turquoise-700"
      : "text-ink hover:bg-bone",
  ].join(" ");
}

function NavItemLink({
  item,
  collapsed,
  onNavigate,
}: {
  item: NavItem;
  collapsed: boolean;
  onNavigate?: () => void;
}) {
  return (
    <NavLink
      to={item.to}
      end={item.end}
      title={collapsed ? item.label : undefined}
      aria-label={collapsed ? item.label : undefined}
      className={({ isActive }) => itemClassName(isActive, collapsed)}
      onClick={onNavigate}
    >
      <NavIcon name={item.icon} className="shrink-0" />
      {collapsed ? null : <span className="truncate">{item.label}</span>}
    </NavLink>
  );
}

export interface SidebarNavProps {
  isAdmin: boolean;
  /** Icon-only rail (768–1023 px). */
  collapsed: boolean;
  onNavigate?: () => void;
}

export function SidebarNav({ isAdmin, collapsed, onNavigate }: SidebarNavProps) {
  const groups = navGroups.filter((group) => !group.adminOnly || isAdmin);

  return (
    <nav aria-label="Principal" className="space-y-5" data-testid="sidebar-nav">
      {groups.map((group) => (
        <div key={group.id} className="space-y-1">
          {collapsed ? (
            <span className="sr-only">{group.label}</span>
          ) : (
            <p className="px-3 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-faint">
              {group.label}
            </p>
          )}
          <div className="space-y-0.5">
            {group.items.map((item) => (
              <NavItemLink
                key={item.to}
                item={item}
                collapsed={collapsed}
                onNavigate={onNavigate}
              />
            ))}
          </div>
        </div>
      ))}
    </nav>
  );
}
