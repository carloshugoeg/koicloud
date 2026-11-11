/** Spanish marketing copy for the public landing. Single source for sections and tests. */

export const LANDING_WHAT_IS =
  "KoiCloud es PostgreSQL 16 gestionado, pensado para agentes.";

export const LANDING_THESIS =
  "Si tu sistema no puede ser operado por agentes hoy en día, nadie lo va a usar.";

export const LANDING_HERO_SUPPORT =
  "Un pond listo en segundos: operable desde la web, la CLI y agentes de IA. Pensado para estudiantes, prototipos y gente que no quiere pelearse con Supabase o Neon.";

export const HOW_IT_WORKS = [
  {
    step: "Paso 1",
    title: "Creas tu cuenta",
    body: "Sandbox gratis al empezar. Los pagos de Micro y Pro son simulados: es un proyecto académico, no hay cobro real.",
    band: "border-t-turquoise-700",
  },
  {
    step: "Paso 2",
    title: "Levantas un pond",
    body: "Encolamos el trabajo, el nodo arranca PostgreSQL 16 en Docker y te devolvemos host, puerto y credenciales en segundos.",
    band: "border-t-green-700",
  },
  {
    step: "Paso 3",
    title: "Operas como quieras",
    body: "Desde la UI, la CLI koicloud o un agente por MCP. Las escrituras piden confirmación; un link temporal se puede revocar al instante.",
    band: "border-t-marigold",
  },
] as const;

export const AGENT_POINTS = [
  {
    title: "MCP listo para Claude Code",
    body: "Tu agente habla con la misma API que la web y la CLI. No hay un segundo camino con reglas distintas.",
  },
  {
    title: "Link temporal limitado a un pond",
    body: "Das acceso acotado a un solo pond. Cuando termina la sesión, lo revocas al instante.",
  },
  {
    title: "Confirmación antes de escribir",
    body: "Las mutaciones proponen un resumen en español y esperan tu confirmación. El agente no ejecuta a ciegas.",
  },
] as const;

export const OPERATE_WAYS = [
  {
    title: "Interfaz web",
    body: "Consola SQL, estado del pond y cadena de conexión sin salir del navegador.",
    accent: "border-t-turquoise-700",
  },
  {
    title: "CLI koicloud",
    body: "Los mismos comandos que usas en demos y scripts. Propose → confirm en cada mutación.",
    accent: "border-t-green-700",
  },
  {
    title: "Agentes de IA",
    body: "MCP para Claude Code y similares. Operás el pond con lenguaje natural y control humano.",
    accent: "border-t-marigold",
  },
] as const;

export const FAQ_ITEMS = [
  {
    q: "¿Es un producto de producción?",
    a: "No. KoiCloud es un DBaaS académico (Universidad Rafael Landívar, 2026). Los pagos están simulados: no hay pasarela ni cobro real.",
  },
  {
    q: "¿Cuánto tarda en quedar listo un pond?",
    a: "En segundos, no en minutos. El nodo levanta PostgreSQL 16 en Docker y te entrega la conexión cuando el job termina.",
  },
  {
    q: "¿Qué puede hacer un agente?",
    a: "Leer y operar el pond por MCP, con un link temporal limitado a ese pond. Toda escritura pide confirmación y el acceso se puede revocar al instante.",
  },
  {
    q: "¿Para quién es?",
    a: "Estudiantes, prototipos y equipos que quieren Postgres gestionado sin la fricción de plataformas más grandes.",
  },
] as const;

export const FINAL_CTA = {
  title: "Abre tu primer pond hoy",
  body: "Sandbox gratis. Si te sirve, Micro o Pro con pago simulado. Misma marca, tres formas de operarlo.",
} as const;
