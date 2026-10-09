import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  downloadInvoicePdf,
  useInvoiceQuery,
  useInvoicesQuery,
  useUsageQuery,
} from "@/api/hooks";
import type { components } from "@/api/schema";
import { problemToMessage } from "@/lib/errors";

type UsagePond = components["schemas"]["UsagePondItem"];
type Invoice = components["schemas"]["InvoiceOut"];

const MONTH_NAMES = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
] as const;

const MONEY_FORMATTER = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 4,
});

function currentMonthValue() {
  const now = new Date();
  const year = now.getUTCFullYear();
  const month = String(now.getUTCMonth() + 1).padStart(2, "0");
  return `${year}-${month}`;
}

function monthLabel(month: string) {
  const [year, monthPart] = month.split("-");
  if (!year || !monthPart) {
    return month;
  }

  const index = Number(monthPart) - 1;
  const name = MONTH_NAMES[index];
  if (!name) {
    return month;
  }

  return `${name} ${year}`;
}

function formatHours(value: number) {
  return value.toFixed(1);
}

function issuedMonth(issuedAt: string) {
  const date = new Date(issuedAt);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  return `${year}-${month}`;
}

function monthOptions(selected: string, extraMonths: string[] = []) {
  const options = new Set<string>([selected, currentMonthValue(), ...extraMonths]);
  const [yearPart, monthPart] = selected.split("-");
  const year = Number(yearPart);
  const month = Number(monthPart);

  if (Number.isFinite(year) && Number.isFinite(month)) {
    for (let offset = 0; offset < 12; offset += 1) {
      const date = new Date(Date.UTC(year, month - 1 - offset, 1));
      const value = `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}`;
      options.add(value);
    }
  }

  return [...options].sort().reverse();
}

function invoiceForMonth(invoices: Invoice[] | undefined, month: string) {
  return invoices?.find((invoice) => issuedMonth(invoice.issued_at) === month);
}

function isEmptyUsage(usage: {
  ponds: UsagePond[];
  total_instance_hours: number;
  total_storage_gb_hours: number;
}) {
  return (
    usage.ponds.length === 0 &&
    usage.total_instance_hours === 0 &&
    usage.total_storage_gb_hours === 0
  );
}

function PondBars({ ponds }: { ponds: UsagePond[] }) {
  const maxHours = Math.max(...ponds.map((pond) => pond.instance_hours), 1);

  return (
    <div
      aria-label="Tendencia de uso por pond"
      className="flex h-40 items-end gap-2 border-b border-line pb-2"
      role="img"
    >
      {ponds.map((pond, index) => {
        const height = Math.max(8, Math.round((pond.instance_hours / maxHours) * 140));
        const tone =
          index % 3 === 0
            ? "bg-turquoise-700"
            : index % 3 === 1
              ? "bg-turquoise-500"
              : "bg-turquoise-300";

        return (
          <div key={pond.pond_id} className="flex min-w-0 flex-1 flex-col items-center gap-2">
            <div
              className={`w-full max-w-12 ${tone}`}
              style={{ height: `${height}px` }}
              title={`${pond.pond_name}: ${formatHours(pond.instance_hours)} h`}
            />
            <span className="w-full truncate text-center font-mono text-[11px] text-ink-muted">
              {pond.pond_name}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function InvoicePaper({
  invoice,
  lines,
}: {
  invoice: Invoice;
  lines: components["schemas"]["InvoiceLineOut"][];
}) {
  return (
    <article className="rounded-md border border-line bg-paper p-6 shadow-[var(--shadow-print)]">
      <header className="flex flex-wrap items-start gap-4 border-b-[3px] border-ink pb-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
            Factura
          </p>
          <h2 className="font-display text-3xl text-ink">KoiCloud</h2>
          <p className="mt-2 text-sm leading-6 text-ink-muted">
            Proyecto académico · Universidad Rafael Landívar
            <br />
            Documento de demostración: no es una factura fiscal.
          </p>
        </div>
        <div className="ml-auto text-right font-mono text-xs leading-5 text-ink-muted">
          <span className="block font-display text-xl text-ink">{invoice.number}</span>
          <span>{new Date(invoice.issued_at).toLocaleString("es-GT")}</span>
          <span className="mt-1 block uppercase tracking-[0.14em]">{invoice.status}</span>
        </div>
      </header>

      <table className="mt-5 w-full text-left text-sm">
        <thead>
          <tr className="border-b border-line text-ink-muted">
            <th className="py-2 font-medium">Concepto</th>
            <th className="py-2 text-right font-medium">Monto</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line) => (
            <tr key={line.id} className="border-b border-line/70">
              <td className="py-3 text-ink">{line.description}</td>
              <td className="py-3 text-right font-mono text-ink">
                {MONEY_FORMATTER.format(line.amount_usd)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <dl className="ml-auto mt-5 w-full max-w-xs space-y-2 text-sm">
        <div className="flex justify-between gap-4">
          <dt className="text-ink-muted">Subtotal</dt>
          <dd className="font-mono text-ink">{MONEY_FORMATTER.format(invoice.subtotal_usd)}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-ink-muted">IVA 12 %</dt>
          <dd className="font-mono text-ink">{MONEY_FORMATTER.format(invoice.iva_usd)}</dd>
        </div>
        <div className="flex justify-between gap-4 border-t border-ink pt-2 font-display text-xl">
          <dt>Total</dt>
          <dd>{MONEY_FORMATTER.format(invoice.total_usd)}</dd>
        </div>
      </dl>
    </article>
  );
}

export function UsoPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const month = searchParams.get("month") || currentMonthValue();
  const usageQuery = useUsageQuery(month);
  const invoicesQuery = useInvoicesQuery();
  const monthInvoice = useMemo(
    () => invoiceForMonth(invoicesQuery.data, month),
    [invoicesQuery.data, month],
  );
  const invoiceMonths = useMemo(
    () =>
      (invoicesQuery.data ?? [])
        .map((invoice) => issuedMonth(invoice.issued_at))
        .filter((value): value is string => Boolean(value)),
    [invoicesQuery.data],
  );
  const invoiceQuery = useInvoiceQuery(monthInvoice?.id);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  const usage = usageQuery.data;
  const empty = usage ? isEmptyUsage(usage) : false;
  const selectableMonths = monthOptions(month, invoiceMonths);

  async function handleDownloadPdf() {
    if (!monthInvoice) {
      return;
    }

    setPdfError(null);
    setDownloading(true);
    try {
      const blob = await downloadInvoicePdf(monthInvoice.id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${monthInvoice.number}.pdf`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      setPdfError(problemToMessage(error));
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
            Consumo
          </p>
          <h2 className="font-display text-4xl text-ink">{monthLabel(month)}</h2>
          <p className="mt-1 text-sm text-ink-muted">
            Horas y almacenamiento del mes, con la factura del mismo período.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-sm text-ink-muted" htmlFor="uso-month">
            Mes
          </label>
          <select
            className="rounded-sm border border-line-control bg-bone-raised px-3 py-2 text-sm text-ink"
            id="uso-month"
            value={month}
            onChange={(event) => {
              setSearchParams({ month: event.target.value });
            }}
          >
            {selectableMonths.map((value) => (
              <option key={value} value={value}>
                {monthLabel(value)}
              </option>
            ))}
          </select>
          <button
            className="rounded-sm border border-turquoise-700 bg-turquoise-700 px-3 py-2 text-sm font-medium text-bone-raised transition-colors duration-instant ease-brand-out hover:bg-turquoise-900 disabled:opacity-50"
            disabled={!monthInvoice || downloading}
            onClick={handleDownloadPdf}
            type="button"
          >
            {downloading ? "Descargando…" : "Descargar factura PDF"}
          </button>
        </div>
      </div>

      {usageQuery.isPending || invoicesQuery.isPending ? (
        <p className="text-sm text-ink-muted">Cargando uso y facturas…</p>
      ) : null}

      {usageQuery.isError ? (
        <p className="text-sm text-ink-muted">{problemToMessage(usageQuery.error)}</p>
      ) : null}

      {pdfError ? (
        <p className="text-sm text-ink" style={{ color: "var(--danger)" }}>
          {pdfError}
        </p>
      ) : null}

      {usage && empty ? (
        <div className="rounded-md border border-dashed border-line bg-bone-raised p-8 text-center">
          <p className="font-display text-2xl text-ink">Sin uso en {monthLabel(month)}</p>
          <p className="mt-2 text-sm text-ink-muted">
            No hay horas de instancia ni almacenamiento registrados para este mes.
          </p>
        </div>
      ) : null}

      {usage && !empty ? (
        <>
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-md border border-line bg-bone-raised p-4">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
                Horas de instancia
              </p>
              <p className="font-display text-4xl text-ink">
                <span data-testid="kpi-instance-hours">
                  {formatHours(usage.total_instance_hours)}
                </span>{" "}
                <span className="text-xl text-ink-muted">h</span>
              </p>
            </div>
            <div className="rounded-md border border-line bg-bone-raised p-4">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
                Almacenamiento · GB-hora
              </p>
              <p className="font-display text-4xl text-ink">
                <span data-testid="kpi-storage-gb-hours">
                  {formatHours(usage.total_storage_gb_hours)}
                </span>{" "}
                <span className="text-xl text-ink-muted">GB·h</span>
              </p>
            </div>
            <div className="rounded-md border border-line bg-bone-raised p-4">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
                Factura del período
              </p>
              <p className="font-display text-4xl text-ink">
                {monthInvoice ? MONEY_FORMATTER.format(monthInvoice.total_usd) : "—"}
              </p>
            </div>
          </div>

          <section className="rounded-md border border-line bg-bone-raised p-4">
            <div className="mb-4">
              <h3 className="font-display text-2xl text-ink">Tendencia del mes</h3>
              <p className="text-sm text-ink-muted">Horas de instancia por pond en el período.</p>
            </div>
            <PondBars ponds={usage.ponds} />
          </section>

          <section className="rounded-md border border-line bg-bone-raised p-4">
            <div className="mb-4">
              <h3 className="font-display text-2xl text-ink">Desglose por pond</h3>
              <p className="text-sm text-ink-muted">Totales del mes por estanque.</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[28rem] text-left text-sm">
                <thead>
                  <tr className="border-b border-line text-ink-muted">
                    <th className="py-2 font-medium">Pond</th>
                    <th className="py-2 text-right font-medium">Horas</th>
                    <th className="py-2 text-right font-medium">GB·h</th>
                  </tr>
                </thead>
                <tbody>
                  {usage.ponds.map((pond) => (
                    <tr key={pond.pond_id} className="border-b border-line/70">
                      <td className="py-3 font-mono text-ink">{pond.pond_name}</td>
                      <td className="py-3 text-right font-mono text-ink">
                        {formatHours(pond.instance_hours)}
                      </td>
                      <td className="py-3 text-right font-mono text-ink">
                        {formatHours(pond.storage_gb_hours)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td className="pt-3 font-medium text-ink">Total</td>
                    <td className="pt-3 text-right font-mono font-medium text-ink">
                      {formatHours(usage.total_instance_hours)}
                    </td>
                    <td className="pt-3 text-right font-mono font-medium text-ink">
                      {formatHours(usage.total_storage_gb_hours)}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </section>
        </>
      ) : null}

      <section className="space-y-3">
        <div>
          <h3 className="font-display text-2xl text-ink">Factura</h3>
          <p className="text-sm text-ink-muted">Subtotal, IVA 12 % y total listos para descargar.</p>
        </div>
        {monthInvoice && invoiceQuery.data ? (
          <InvoicePaper invoice={invoiceQuery.data.invoice} lines={invoiceQuery.data.lines} />
        ) : (
          <p className="rounded-md border border-dashed border-line bg-bone-raised p-6 text-sm text-ink-muted">
            No hay factura emitida para {monthLabel(month)}.
          </p>
        )}
      </section>
    </div>
  );
}
