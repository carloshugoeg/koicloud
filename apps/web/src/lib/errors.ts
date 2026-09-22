import type { components } from "@/api/schema";

export type ApiProblem = components["schemas"]["ErrorResponse"];

const CATALOG: Record<ApiProblem["code"], string> = {
  invalid_credentials: "Correo o contraseña incorrectos.",
  email_not_verified: "Verificá tu correo antes de continuar.",
  account_suspended: "Tu cuenta está suspendida.",
  token_expired: "Tu sesión expiró. Iniciá sesión otra vez.",
  token_invalid: "El token enviado no es válido.",
  email_taken: "Ese correo ya está registrado.",
  password_too_weak: "La contraseña no cumple los requisitos mínimos.",
  plan_required: "Necesitás una suscripción activa para continuar.",
  quota_exceeded: "Alcanzaste el máximo de ponds de tu plan.",
  pond_name_taken: "Ese nombre de pond ya está en uso.",
  pond_not_found: "No encontramos ese pond.",
  pond_busy: "Ese pond ya tiene una operación en curso.",
  node_unavailable: "No hay un nodo disponible para ejecutar esa acción.",
  sql_readonly_violation: "La consulta intenta escribir datos en modo lectura.",
  sql_timeout: "La consulta excedió el tiempo máximo permitido.",
  confirmation_required: "Esta acción necesita confirmación explícita.",
  confirmation_not_found: "No encontramos la confirmación solicitada.",
  confirmation_expired: "La confirmación ya expiró.",
  confirmation_action_mismatch: "La confirmación no corresponde a esta acción.",
  agent_disabled: "El acceso del agente está desactivado.",
  agent_bad_credentials: "Las credenciales del agente no son válidas.",
  not_owner: "No tenés permiso para ver ese recurso.",
  admin_only: "Esta pantalla es solo para administradores.",
  rate_limited: "Hiciste demasiados intentos. Esperá un momento.",
  disk_full: "No hay espacio suficiente para completar la operación.",
  internal_error: "Algo salió mal. Revisá los logs e intentá de nuevo.",
};

export class ApiError extends Error {
  problem: ApiProblem | null;

  constructor(problem: unknown) {
    super(problemToMessage(problem));
    this.name = "ApiError";
    this.problem = isApiProblem(problem) ? problem : null;
  }
}

function isApiProblem(value: unknown): value is ApiProblem {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as { code?: unknown }).code === "string" &&
    typeof (value as { message?: unknown }).message === "string"
  );
}

export function problemToMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (isApiProblem(error)) {
    return CATALOG[error.code] ?? error.message;
  }

  if (error instanceof TypeError) {
    return "No pudimos conectar con el control plane.";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Ocurrió un error inesperado.";
}
