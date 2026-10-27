# Decisiones (amendment r3+)

Registro corto de decisiones de contrato aprobadas vía CCR. Los ADRs A-01..A-12
siguen en [`docs/adr/`](adr/).

## 1. Soft-delete de users (CCR [#126](https://github.com/carloshugoeg/koicloud/issues/126))

**Decision:** `users.deleted_at` (timestamptz null) más tombstone de email
`email || '.deleted.' || id`. Login rechaza filas con `deleted_at IS NOT NULL`.
`DELETE /me` cancela la suscripción viva, encola deletes de ponds, revoca refresh
y escribe audit `user.delete`.

**Why:** conserva FKs (invoices, audit, ponds históricos) y libera el correo para
un registro futuro.

**Rejected:** hard-delete (rompe FKs) y reusar `status=suspended` como “borrado”
(no libera email ni cancela ponds/subs).
