import { MenuIcon } from "@/app/layout/nav-icons";

export interface AppHeaderProps {
  title: string;
  userName: string;
  userEmail: string;
  onLogout: () => void;
  onOpenNav: () => void;
  showMenuButton: boolean;
}

export function AppHeader({
  title,
  userName,
  userEmail,
  onLogout,
  onOpenNav,
  showMenuButton,
}: AppHeaderProps) {
  return (
    <header
      className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-bone px-4 lg:px-8"
      style={{ minHeight: "var(--header-h)" }}
      data-testid="app-header"
    >
      <div className="flex min-w-0 items-center gap-3">
        {showMenuButton ? (
          <button
            type="button"
            className="rounded-sm border border-line-control bg-bone-raised p-2 text-ink transition-colors duration-instant ease-brand-out hover:border-turquoise-700 hover:text-turquoise-700"
            aria-label="Abrir menú"
            data-testid="nav-menu-button"
            onClick={onOpenNav}
          >
            <MenuIcon />
          </button>
        ) : null}
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-ink-muted">
            Control plane
          </p>
          <h1 className="truncate font-display text-2xl text-ink sm:text-3xl">{title}</h1>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden text-right sm:block">
          <p className="text-sm font-medium text-ink">{userName}</p>
          <p className="text-xs text-ink-muted">{userEmail}</p>
        </div>
        <button
          className="rounded-sm border border-line-control bg-bone-raised px-3 py-2 text-sm font-medium text-ink transition-colors duration-instant ease-brand-out hover:border-turquoise-700 hover:text-turquoise-700"
          onClick={onLogout}
          type="button"
        >
          Cerrar sesión
        </button>
      </div>
    </header>
  );
}
