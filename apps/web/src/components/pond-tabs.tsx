import { Link } from "react-router-dom";

const POND_TABS = [
  { id: "resumen", label: "Resumen", href: (pondId: string) => `/app/ponds/${pondId}` },
  { id: "respaldos", label: "Respaldos", href: (pondId: string) => `/app/ponds/${pondId}/backups` },
  { id: "consola", label: "Consola", href: (pondId: string) => `/app/ponds/${pondId}/console` },
] as const;

export type PondTabId = (typeof POND_TABS)[number]["id"];

function tabClass(active: boolean) {
  const base =
    "inline-flex h-8 items-center rounded-sm px-3 text-sm transition-colors duration-instant ease-brand-out focus-visible:outline-none focus-visible:shadow-focus";
  if (active) {
    return `${base} border-b-2 border-turquoise-700 bg-bone-sunk font-medium text-ink hover:bg-bone`;
  }
  return `${base} text-turquoise-700 hover:bg-bone-sunk`;
}

export function PondTabs({ pondId, active }: { pondId: string; active: PondTabId }) {
  return (
    <nav aria-label="Secciones del pond" className="mt-3 flex flex-wrap gap-1" data-testid="pond-tabs">
      {POND_TABS.map((tab) => {
        const current = tab.id === active;
        return (
          <Link
            key={tab.id}
            to={tab.href(pondId)}
            aria-current={current ? "page" : undefined}
            className={tabClass(current)}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
