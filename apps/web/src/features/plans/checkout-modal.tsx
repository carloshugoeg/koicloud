import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSubscribeMutation, type PlanOut, type SubscribeResponse } from "@/api/hooks";
import { cardDigits, cardNumberError, cvvError, expiryError, nitError } from "@/lib/billing-checks";
import { ApiError, problemToMessage } from "@/lib/errors";
import { formatPrice, formatPricePeriod } from "@/lib/format-price";

export interface CheckoutModalProps {
  plan: PlanOut;
  onClose: () => void;
  onSuccess: (res: SubscribeResponse) => void;
}

export function CheckoutModal({ plan, onClose, onSuccess }: CheckoutModalProps) {
  const navigate = useNavigate();
  const subscribeMutation = useSubscribeMutation();
  const [nit, setNit] = useState("");
  const [cardNumber, setCardNumber] = useState("");
  const [cardExpiry, setCardExpiry] = useState("");
  const [cardCvc, setCardCvc] = useState("");
  const [issued, setIssued] = useState<SubscribeResponse | null>(null);
  const [fieldErrors, setFieldErrors] = useState<{ nit?: string; card?: string; expiry?: string; cvc?: string }>({});

  async function handleCheckout(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedNit = nit.trim();
    const number = cardDigits(cardNumber);
    const nextErrors = {
      nit: trimmedNit ? nitError(trimmedNit) ?? undefined : undefined,
      card: cardNumberError(cardNumber) ?? undefined,
      expiry: expiryError(cardExpiry) ?? undefined,
      cvc: cvvError(cardNumber, cardCvc) ?? undefined,
    };
    setFieldErrors(nextErrors);
    if (nextErrors.nit || nextErrors.card || nextErrors.expiry || nextErrors.cvc) {
      return;
    }
    try {
      const res = await subscribeMutation.mutateAsync({
        plan_id: plan.id,
        nit: trimmedNit ? trimmedNit : null,
        card: { number, expiry: cardExpiry.trim(), cvc: cardCvc.trim() },
      });
      setIssued(res);
    } catch {
      // The alert reads subscribeMutation.error.
    }
  }

  const err = subscribeMutation.error;
  const problemCode = err instanceof ApiError ? err.problem?.code : undefined;

  if (issued) {
    const { invoice } = issued;
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/30" role="dialog" aria-modal="true" aria-labelledby="checkout-title">
        <div className="w-full max-w-lg rounded-sm border border-line-control bg-bone-raised p-6 shadow-dialog">
          <h2 id="checkout-title" className="font-display text-2xl text-ink">
            Factura {invoice.number}
          </h2>
          <p className="mt-1 text-sm text-ink-muted">Líneas e importes desde el API (`InvoiceOut`).</p>
          <p className="mt-1 font-mono text-xs text-ink-muted">
            NIT: <span className="text-ink">{invoice.nit ?? "—"}</span>
          </p>
          <div className="mt-4 rounded-sm border border-line bg-paper p-4" data-testid="checkout-invoice-from-api">
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-ink-muted">Subtotal</dt>
                <dd className="font-mono tabular-nums text-ink">
                  {formatPrice({ unit_price: invoice.subtotal_usd, currency: "USD" })}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-ink-muted">IVA 12 %</dt>
                <dd className="font-mono tabular-nums text-ink">
                  {formatPrice({ unit_price: invoice.iva_usd, currency: "USD" })}
                </dd>
              </div>
              <div className="flex justify-between gap-4 border-t border-line pt-2 font-medium">
                <dt className="text-ink">Total</dt>
                <dd className="font-mono tabular-nums text-ink" data-testid="checkout-invoice-total">
                  {formatPrice({ unit_price: invoice.total_usd, currency: "USD" })}
                </dd>
              </div>
            </dl>
          </div>
          <div className="mt-6 flex justify-end">
            <button
              type="button"
              onClick={() => {
                onSuccess(issued);
                onClose();
                navigate("/app/ponds/new");
              }}
              className="h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised hover:bg-turquoise-900"
            >
              Crear mi primer pond →
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/30" role="dialog" aria-modal="true" aria-labelledby="checkout-title">
      <div className="w-full max-w-lg rounded-sm border border-line-control bg-bone-raised p-6 shadow-dialog">
        <div className="flex items-center justify-between border-b border-line pb-3">
          <h2 id="checkout-title" className="font-display text-2xl text-ink">
            Contratar plan {plan.name}
          </h2>
          <button type="button" onClick={onClose} aria-label="Cerrar diálogo" className="text-sm font-medium text-ink-muted hover:text-ink">
            ✕
          </button>
        </div>

        <div className="mt-4 rounded-sm border-l-4 border-marigold bg-marigold/10 p-3 text-xs font-medium text-ink">
          Pago simulado: no se realiza ningún cobro real.
        </div>

        <div className="mt-4 rounded-sm border border-line bg-paper p-4" data-testid="checkout-catalog-price">
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-ink-muted">Precio de catálogo</p>
          <p className="mt-2 font-display text-2xl tabular-nums text-ink">
            {formatPrice(plan)}{" "}
            <span className="text-sm font-sans font-normal text-ink-muted">{formatPricePeriod(plan)}</span>
          </p>
          <p className="mt-2 text-xs text-ink-muted">
            Al confirmar, la factura del API trae los importes. Sin math de negocio en el navegador.
          </p>
        </div>

        <form onSubmit={handleCheckout} className="mt-4 space-y-4">
          {subscribeMutation.isError ? (
            <div className="rounded-sm border-l-4 border-danger bg-paper p-3 text-xs" role="alert">
              <p className="font-medium text-ink">{problemToMessage(subscribeMutation.error)}</p>
              {problemCode ? (
                <p className="mt-1 font-mono text-ink-faint">{problemCode}</p>
              ) : null}
            </div>
          ) : null}

          <div>
            <label htmlFor="checkout-nit" className="block text-xs font-medium text-ink-muted">
              NIT (opcional)
            </label>
            <input
              id="checkout-nit"
              name="nit"
              type="text"
              value={nit}
              onChange={(e) => setNit(e.target.value)}
              placeholder="1000002-K"
              maxLength={32}
              aria-invalid={fieldErrors.nit ? true : undefined}
              className="mt-1 h-9 w-full rounded-sm border border-line-control bg-paper px-3 text-sm text-ink outline-none focus:border-turquoise-700 focus:shadow-focus"
            />
            {fieldErrors.nit ? <p className="mt-1 text-xs text-danger">{fieldErrors.nit}</p> : null}
            <p className="mt-1 text-xs text-ink-muted">CF si no tienes NIT</p>
          </div>

          <div>
            <label htmlFor="checkout-card" className="block text-xs font-medium text-ink-muted">
              Número de tarjeta simulada
            </label>
            <input
              id="checkout-card"
              name="card"
              type="text"
              required
              value={cardNumber}
              onChange={(e) => setCardNumber(e.target.value)}
              placeholder="4242 4242 4242 4242"
              aria-invalid={fieldErrors.card ? true : undefined}
              className="mt-1 h-9 w-full rounded-sm border border-line-control bg-paper px-3 font-mono text-sm text-ink outline-none focus:border-turquoise-700 focus:shadow-focus"
            />
            {fieldErrors.card ? <p className="mt-1 text-xs text-danger">{fieldErrors.card}</p> : null}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="checkout-expiry" className="block text-xs font-medium text-ink-muted">
                Expiración
              </label>
              <input
                id="checkout-expiry"
                name="expiry"
                type="text"
                required
                value={cardExpiry}
                onChange={(e) => setCardExpiry(e.target.value)}
                placeholder="MM/AA"
                aria-invalid={fieldErrors.expiry ? true : undefined}
                className="mt-1 h-9 w-full rounded-sm border border-line-control bg-paper px-3 font-mono text-sm text-ink outline-none focus:border-turquoise-700 focus:shadow-focus"
              />
              {fieldErrors.expiry ? <p className="mt-1 text-xs text-danger">{fieldErrors.expiry}</p> : null}
            </div>
            <div>
              <label htmlFor="checkout-cvc" className="block text-xs font-medium text-ink-muted">
                CVC
              </label>
              <input
                id="checkout-cvc"
                name="cvc"
                type="text"
                required
                value={cardCvc}
                onChange={(e) => setCardCvc(e.target.value)}
                placeholder="123"
                aria-invalid={fieldErrors.cvc ? true : undefined}
                className="mt-1 h-9 w-full rounded-sm border border-line-control bg-paper px-3 font-mono text-sm text-ink outline-none focus:border-turquoise-700 focus:shadow-focus"
              />
              {fieldErrors.cvc ? <p className="mt-1 text-xs text-danger">{fieldErrors.cvc}</p> : null}
            </div>
          </div>

          <div className="mt-6 flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={subscribeMutation.isPending}
              className="h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-ink hover:bg-bone"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={subscribeMutation.isPending}
              className="h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised transition-colors duration-instant hover:bg-turquoise-900 disabled:opacity-50"
            >
              {subscribeMutation.isPending ? "Contratando…" : "Confirmar contratación"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
