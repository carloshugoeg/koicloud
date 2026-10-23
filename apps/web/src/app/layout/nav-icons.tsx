import type { NavIconName } from "@/app/layout/nav-config";

/** Inline lucide-style paths (stroke 1.5) — no new package dependency. */
const paths: Record<NavIconName, string> = {
  ponds:
    "M4 10c0-3.5 3.5-6 8-6s8 2.5 8 6-3.5 6-8 6-8-2.5-8-6Zm0 0c0 2 1.5 3.5 4 4.5M20 10c0 2-1.5 3.5-4 4.5M6 18c1.5.7 3.5 1 6 1s4.5-.3 6-1",
  create: "M12 5v14M5 12h14",
  usage: "M4 19V5M4 19h16M8 15v-4M12 15V9M16 15v-7",
  billing: "M4 7h16v12H4zM4 11h16M8 15h4",
  plans: "M12 3 4 7v5c0 4.5 3.2 7.8 8 9 4.8-1.2 8-4.5 8-9V7l-8-4Z",
  agent: "M12 8a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM4 21v-1a6 6 0 0 1 12 0v1M18 11v4M20 13h-4",
  account: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM4 21v-1a6 6 0 0 1 12 0v1",
  users:
    "M16 21v-1a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v1M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM22 21v-1a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75",
  subscriptions: "M4 6h16M4 12h16M4 18h10",
  adminPonds: "M3 10h18M7 10V6a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v4M5 10v8a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-8",
  audit: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
};

interface NavIconProps {
  name: NavIconName;
  className?: string;
}

export function NavIcon({ name, className }: NavIconProps) {
  return (
    <svg
      aria-hidden
      className={className}
      fill="none"
      height="16"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.5"
      viewBox="0 0 24 24"
      width="16"
    >
      <path d={paths[name]} />
    </svg>
  );
}

export function MenuIcon({ className }: { className?: string }) {
  return (
    <svg
      aria-hidden
      className={className}
      fill="none"
      height="20"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.5"
      viewBox="0 0 24 24"
      width="20"
    >
      <path d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );
}

export function CloseIcon({ className }: { className?: string }) {
  return (
    <svg
      aria-hidden
      className={className}
      fill="none"
      height="20"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.5"
      viewBox="0 0 24 24"
      width="20"
    >
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  );
}
