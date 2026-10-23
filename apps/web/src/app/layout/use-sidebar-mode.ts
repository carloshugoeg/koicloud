import { useEffect, useState } from "react";

export type SidebarMode = "sheet" | "rail" | "expanded";

function readMode(width: number): SidebarMode {
  if (width < 768) return "sheet";
  if (width < 1024) return "rail";
  return "expanded";
}

/** §5.1: <768 Sheet · <1024 icon rail 72px · ≥1024 full 264px. */
export function useSidebarMode(): SidebarMode {
  const [mode, setMode] = useState<SidebarMode>(() =>
    typeof window === "undefined" ? "expanded" : readMode(window.innerWidth),
  );

  useEffect(() => {
    const onResize = () => setMode(readMode(window.innerWidth));
    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  return mode;
}
