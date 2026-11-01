type PondRiskZoneProps = {
  disabled: boolean;
  onDelete: () => void;
};

export function PondRiskZone({ disabled, onDelete }: PondRiskZoneProps) {
  return (
    <section
      className="rounded-md border border-line bg-bone-raised p-5"
      data-testid="pond-risk-zone"
    >
      <h3 className="font-display text-xl text-ink">Zona de riesgo</h3>
      <p className="mt-1 text-sm text-ink-muted">
        Al eliminar encolamos primero un respaldo <span className="font-mono">pre_delete</span> y luego
        el borrado del contenedor. Te pediremos escribir el nombre del pond.
      </p>
      <button
        type="button"
        className="mt-4 h-8 rounded-sm border border-danger bg-bone-raised px-3 text-sm font-medium text-danger disabled:border-line-control disabled:text-ink-faint"
        disabled={disabled}
        onClick={onDelete}
        data-testid="open-delete-pond-risk"
      >
        Eliminar pond…
      </button>
    </section>
  );
}
