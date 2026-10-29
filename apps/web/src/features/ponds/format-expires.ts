const GUATEMALA = "America/Guatemala";

export interface ExpiresPresentation {
  label: string;
  title?: string;
}

export function formatExpires(expiresAt: string | null | undefined): ExpiresPresentation {
  if (!expiresAt) return { label: "—" };
  const instant = new Date(expiresAt);
  if (Number.isNaN(instant.getTime())) return { label: "—" };

  const title = guatemalaTitle(instant);
  const now = new Date();
  if (instant.getTime() < now.getTime()) return { label: "vencido", title };

  const days = guatemalaCalendarDays(now, instant);
  if (days <= 0) return { label: "hoy", title };
  return { label: `en ${days} d`, title };
}

function guatemalaTitle(instant: Date): string {
  const parts = guatemalaParts(instant);
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}`;
}

function guatemalaCalendarDays(from: Date, to: Date): number {
  const start = guatemalaParts(from);
  const end = guatemalaParts(to);
  const startDay = Date.UTC(Number(start.year), Number(start.month) - 1, Number(start.day));
  const endDay = Date.UTC(Number(end.year), Number(end.month) - 1, Number(end.day));
  return Math.round((endDay - startDay) / 86_400_000);
}

function guatemalaParts(instant: Date) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: GUATEMALA,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(instant);
  const value = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value ?? "";
  const hour = value("hour") === "24" ? "00" : value("hour");
  return {
    year: value("year"),
    month: value("month"),
    day: value("day"),
    hour,
    minute: value("minute"),
  };
}
