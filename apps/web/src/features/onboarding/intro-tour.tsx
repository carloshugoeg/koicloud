import { useEffect, useState } from "react";
import {
  clearIntroTourDone,
  isIntroTourDone,
  markIntroTourDone,
} from "@/features/onboarding/intro-tour-storage";
import {
  consumeIntroTourReplay,
  subscribeIntroTourReplay,
} from "@/features/onboarding/intro-tour-controller";
import { useAuthStore } from "@/lib/auth-store";

const CARDS = [
  {
    title: "Bienvenido a KoiCloud",
    body: "Tu panel para ponds PostgreSQL reales en contenedores. Tres minutos y ya sabés dónde está cada cosa.",
  },
  {
    title: "Estanque, consumo y cuenta",
    body: "Creás ponds en Estanque, revisás el plan en Uso y facturación, y actualizás tus datos en Cuenta.",
  },
  {
    title: "Un recorrido guiado",
    body: "Después de estas tarjetas te señalamos los tres atajos de la barra lateral. Podés omitirlo cuando quieras.",
  },
] as const;

const COACHMARKS = [
  { target: "ponds", text: "Aquí ves tus ponds" },
  { target: "plans", text: "Aquí ves tus planes" },
  { target: "account", text: "Aquí ves tu cuenta" },
] as const;

type Phase =
  | { kind: "cards"; index: number }
  | { kind: "coach"; index: number };

type TourSession = {
  userId: string;
  phase: Phase;
};

function CoachHighlight({ target }: { target: string }) {
  const [box, setBox] = useState<DOMRect | null>(null);

  useEffect(() => {
    function measure() {
      const el = document.querySelector(`[data-tour-target="${target}"]`);
      setBox(el instanceof HTMLElement ? el.getBoundingClientRect() : null);
    }
    const frame = window.requestAnimationFrame(measure);
    window.addEventListener("resize", measure);
    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", measure);
    };
  }, [target]);

  if (!box) {
    return null;
  }

  return (
    <div
      aria-hidden
      className="pointer-events-none fixed z-[61] rounded-sm border-2 border-turquoise-700 shadow-focus"
      style={{
        top: box.top - 4,
        left: box.left - 4,
        width: box.width + 8,
        height: box.height + 8,
      }}
    />
  );
}

export function IntroTour() {
  const userId = useAuthStore((state) => state.session?.user.id);
  const [session, setSession] = useState<TourSession | null>(null);

  useEffect(() => {
    if (!userId) {
      return;
    }
    const activeUserId = userId;

    function start() {
      setSession({ userId: activeUserId, phase: { kind: "cards", index: 0 } });
    }

    function openIfNeeded() {
      const replay = consumeIntroTourReplay();
      if (replay) {
        clearIntroTourDone(activeUserId);
        start();
        return;
      }
      if (!isIntroTourDone(activeUserId)) {
        start();
      }
    }

    const timer = window.setTimeout(openIfNeeded, 0);
    const unsubscribe = subscribeIntroTourReplay(openIfNeeded);
    return () => {
      window.clearTimeout(timer);
      unsubscribe();
    };
  }, [userId]);

  if (!userId || !session || session.userId !== userId) {
    return null;
  }

  const activeUserId = userId;
  const { phase } = session;

  function finish() {
    markIntroTourDone(activeUserId);
    setSession(null);
  }

  function goNext() {
    if (phase.kind === "cards") {
      if (phase.index < CARDS.length - 1) {
        setSession({
          userId: activeUserId,
          phase: { kind: "cards", index: phase.index + 1 },
        });
        return;
      }
      setSession({ userId: activeUserId, phase: { kind: "coach", index: 0 } });
      return;
    }
    if (phase.index < COACHMARKS.length - 1) {
      setSession({
        userId: activeUserId,
        phase: { kind: "coach", index: phase.index + 1 },
      });
      return;
    }
    finish();
  }

  if (phase.kind === "cards") {
    const card = CARDS[phase.index];
    return (
      <div
        className="fixed inset-0 z-[60] flex items-center justify-center bg-ink/30 px-4"
        data-testid="intro-tour"
        role="dialog"
        aria-modal="true"
        aria-labelledby="intro-tour-title"
      >
        <div
          className="w-full max-w-md rounded-md border border-line bg-bone-raised p-6 shadow-dialog"
          data-testid="intro-tour-cards"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-ink-muted">
            Recorrido {phase.index + 1} / {CARDS.length}
          </p>
          <h2 id="intro-tour-title" className="mt-2 font-display text-2xl text-ink">
            {card.title}
          </h2>
          <p className="mt-2 text-sm text-ink-muted">{card.body}</p>
          <div className="mt-6 flex flex-wrap justify-end gap-2">
            <button
              type="button"
              className="h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-ink"
              onClick={finish}
            >
              Omitir
            </button>
            <button
              type="button"
              className="h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised"
              onClick={goNext}
            >
              Siguiente
            </button>
          </div>
        </div>
      </div>
    );
  }

  const coach = COACHMARKS[phase.index];
  const isLast = phase.index === COACHMARKS.length - 1;

  return (
    <div className="fixed inset-0 z-[60]" data-testid="intro-tour" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-ink/20" aria-hidden />
      <CoachHighlight target={coach.target} />
      <div
        className="absolute bottom-6 left-1/2 z-[62] w-[min(100%-2rem,24rem)] -translate-x-1/2 rounded-md border border-line bg-bone-raised p-4 shadow-dialog sm:left-[calc(var(--sidebar-w)+1.5rem)] sm:translate-x-0"
        data-testid="intro-tour-coachmark"
      >
        <p className="text-sm font-medium text-ink">{coach.text}</p>
        <div className="mt-4 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            className="h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-ink"
            onClick={finish}
          >
            Omitir
          </button>
          <button
            type="button"
            className="h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised"
            onClick={goNext}
          >
            {isLast ? "Listo" : "Siguiente"}
          </button>
        </div>
      </div>
    </div>
  );
}
