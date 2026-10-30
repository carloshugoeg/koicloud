import type { components } from "@/api/schema";
import { formatPrice } from "@/lib/format-price";

type Invoice = components["schemas"]["InvoiceOut"];
type InvoiceLine = components["schemas"]["InvoiceLineOut"];

function formatUsd(amount: number): string {
  return formatPrice({ unit_price: amount, currency: "USD" });
}

export function InvoicePaper({
  invoice,
  lines,
}: {
  invoice: Invoice;
  lines: InvoiceLine[];
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
          <span className="mt-1 block">
            NIT: <span className="text-ink">{invoice.nit ?? "—"}</span>
          </span>
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
              <td className="py-3 text-right font-mono tabular-nums text-ink">
                {formatUsd(line.amount_usd)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <dl className="ml-auto mt-5 w-full max-w-xs space-y-2 text-sm">
        <div className="flex justify-between gap-4">
          <dt className="text-ink-muted">Subtotal</dt>
          <dd className="font-mono tabular-nums text-ink">{formatUsd(invoice.subtotal_usd)}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-ink-muted">IVA 12 %</dt>
          <dd className="font-mono tabular-nums text-ink">{formatUsd(invoice.iva_usd)}</dd>
        </div>
        <div className="flex justify-between gap-4 border-t border-ink pt-2 font-display text-xl">
          <dt>Total</dt>
          <dd className="tabular-nums">{formatUsd(invoice.total_usd)}</dd>
        </div>
      </dl>
    </article>
  );
}
