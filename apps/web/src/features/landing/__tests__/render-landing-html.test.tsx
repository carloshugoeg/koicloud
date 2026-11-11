import { renderLandingHtml } from "@/features/landing/render-landing-html";

describe("CA8 renderLandingHtml", () => {
  it("renders visible landing markup from LandingPage (no hand-committed fragment)", () => {
    const html = renderLandingHtml();

    expect(html).toContain('data-landing-prerender="true"');
    expect(html).toContain("KoiCloud es PostgreSQL 16 gestionado, pensado para agentes.");
    expect(html).toContain("Cómo funciona");
    expect(html).toContain("Crear cuenta");
    expect(html).toContain("Planes · precio y vigencia");
    expect(html).toContain("Creas tu cuenta");
    expect(html).toContain("Hecho para agentes");
    expect(html).toContain('href="/login"');
    expect(html).toContain('href="/register"');
  });
});

