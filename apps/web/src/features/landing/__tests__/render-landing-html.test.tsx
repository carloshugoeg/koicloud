import { renderLandingHtml } from "@/features/landing/render-landing-html";

describe("CA8 renderLandingHtml", () => {
  it("renders visible landing markup from LandingPage (no hand-committed fragment)", () => {
    const html = renderLandingHtml();

    expect(html).toContain('data-landing-prerender="true"');
    expect(html).toContain("Tu Postgres en línea antes de que se enfríe el café.");
    expect(html).toContain("Cómo funciona");
    expect(html).toContain("Crear cuenta");
    expect(html).toContain("Planes · precio y vigencia");
    expect(html).toContain("Contratas un plan");
    expect(html).toContain('href="/login"');
    expect(html).toContain('href="/register"');
  });
});
