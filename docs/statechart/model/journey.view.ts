const N: Record<string, string> = { login: "Login", list: "Pond list", resumen: "Pond · Resumen",
  respaldos: "Pond · Respaldos", consola: "Pond · Consola", billing: "Uso y facturación",
  plans: "Planes", checkout: "Checkout", invoice: "Invoice" };
const C: Record<string, string> = { editing: "Checkout", invalid_nit: "Checkout · NIT inválido",
  declined: "Checkout · tarjeta rechazada", issued: "Invoice issued" };
export const title = "KoiCloud user journey";
export const state = (v: any) => (v.co !== "closed" ? C[v.co] : N[v.screen]);
export const group = (v: any) => (v.screen === "login" ? "auth" : ["resumen","respaldos","consola"].includes(v.screen) ? "pond" : v.co !== "closed" || v.screen === "plans" || v.screen === "billing" ? "money" : "nav");
export const colors = { auth: "pink", pond: "teal", money: "yellow", nav: "blue" };
export const step = (a: string, f: any, t: any) => {
  if (t.reloadLost && !f.reloadLost) return "refresh fails and you are logged out";
  if (f.auth === "in" && t.auth === "out") return null; // log out: available everywhere, hidden
  if (f.auth === "out" && t.auth === "in") return "you log in";
  if (f.co !== t.co) {
    if (t.co === "editing") return "you pick a plan";
    if (t.co === "invalid_nit") return "you pay with a bad NIT (422)";
    if (t.co === "declined") return "you pay and the card is declined";
    if (t.co === "issued") return t.chargedBadCard && !f.chargedBadCard ? "you pay with a bad card and it goes through" : "you pay with valid NIT and card";
    if (f.co === "issued") return "you see the invoice";
    return "you cancel checkout";
  }
  if (t.screen === "resumen" && f.screen === "list") return "you open a pond";
  if (t.screen === "list") return "you go to the pond list";
  if (t.screen === "billing") return "you open Uso y facturación";
  if (t.screen === "plans") return f.screen === "billing" ? "you press Cambiar de plan" : "you press Planes in the sidebar";
  if (["resumen","respaldos","consola"].includes(t.screen)) return `you press the ${N[t.screen].split(" · ")[1]} tab`;
  return null;
};
