import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSubscribeMutation, type PlanOut, type SubscribeResponse } from "@/api/hooks";
import { formatPrice } from "@/lib/format-price";
import { ApiError, problemToMessage } from "@/lib/errors";

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
  const [acknowledged, setAcknowledged] = useState(false);
  const priceLabel = formatPrice(plan);
  const postpaid = plan.postpaid && plan.price_monthly_usd === 0;

  async function handleCheckout(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const res = await subscribeMutation.mutateAsync({ plan_id: plan.id });
      onSuccess(res);
      navigate("/app/ponds/new");
    } catch {
      // Manejado con subscribeMutation.error
    }
  }

  const err = subscribeMutation.error;
  const problemCode = err instanceof ApiError ? err.problem?.code : undefined;

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

        <div className="mt-4 rounded-sm border border-line bg-paper p-4" data-testid="checkout-preview">
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-ink-muted">Vista previa</p>
          {postpaid ? (
            <p className="mt-2 text-sm text-ink">Pospago. El importe se cierra con el período.</p>
          ) : (
            <div className="mt-2 flex justify-between text-sm">
              <span className="text-ink-muted">Total del período</span>
              <span className="font-mono tabular-nums text-ink">{priceLabel}</span>
            </div>
          )}
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
              placeholder="0614-220999-101-3"
              className="mt-1 h-9 w-full rounded-sm border border-line-control bg-paper px-3 text-sm text-ink outline-none focus:border-turquoise-700"
            />
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
              placeholder="4242 •••• •••• 4242"
              className="mt-1 h-9 w-full rounded-sm border border-line-control bg-paper px-3 font-mono text-sm text-ink outline-none focus:border-turquoise-700"
            />
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
                className="mt-1 h-9 w-full rounded-sm border border-line-control bg-paper px-3 font-mono text-sm text-ink outline-none focus:border-turquoise-700"
              />
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
                className="mt-1 h-9 w-full rounded-sm border border-line-control bg-paper px-3 font-mono text-sm text-ink outline-none focus:border-turquoise-700"
              />
            </div>
          </div>

          <label className="flex items-start gap-2 text-sm text-ink">
            <input
              type="checkbox"
              className="mt-1"
              checked={acknowledged}
              onChange={(event) => setAcknowledged(event.target.checked)}
            />
            <span>Entiendo que el cobro es simulado y que la factura es un documento de demostración.</span>
          </label>

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
              disabled={!acknowledged || subscribeMutation.isPending}
              className="h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised transition-colors duration-instant hover:bg-turquoise-900 disabled:bg-bone-sunk disabled:text-ink-faint"
            >
              {subscribeMutation.isPending ? "Contratando…" : "Confirmar contratación"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
