import { useState } from "react";
import { PlansPage } from "@/features/plans/plans-page";

export function PlanSection() {
  const [open, setOpen] = useState(false);

  return (
    <section className="space-y-4" aria-labelledby="current-plan-title">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 id="current-plan-title" className="font-display text-2xl text-ink">
          Tu plan actual
        </h2>
        <button
          type="button"
          aria-expanded={open}
          onClick={() => setOpen(true)}
          className="h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised hover:bg-turquoise-900 focus:shadow-focus"
        >
          Cambiar de plan
        </button>
      </div>
      {open ? <PlansPage /> : null}
    </section>
  );
}
