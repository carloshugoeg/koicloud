import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bone: "var(--bone)",
        "bone-raised": "var(--bone-raised)",
        "bone-sunk": "var(--bone-sunk)",
        paper: "var(--paper)",
        ink: "var(--ink)",
        "ink-muted": "var(--ink-muted)",
        "ink-faint": "var(--ink-faint)",
        line: "var(--line)",
        "line-control": "var(--line-control)",
        turquoise: {
          100: "var(--turquoise-100)",
          300: "var(--turquoise-300)",
          500: "var(--turquoise-500)",
          700: "var(--turquoise-700)",
          900: "var(--turquoise-900)",
        },
        green: {
          100: "var(--green-100)",
          500: "var(--green-500)",
          700: "var(--green-700)",
          900: "var(--green-900)",
        },
        koi: "var(--koi)",
        "koi-soft": "var(--koi-soft)",
        marigold: "var(--marigold)",
        lagoon: "var(--lagoon)",
        ok: "var(--ok)",
        warn: "var(--warn)",
        danger: "var(--danger)",
        "danger-soft": "var(--danger-soft)",
      },
      fontFamily: {
        display: ["var(--font-display)"],
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
      },
      spacing: {
        1: "var(--space-1)",
        2: "var(--space-2)",
        3: "var(--space-3)",
        4: "var(--space-4)",
        5: "var(--space-5)",
        6: "var(--space-6)",
        7: "var(--space-7)",
        8: "var(--space-8)",
      },
      borderRadius: {
        xs: "var(--radius-xs)",
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
      },
      boxShadow: {
        print: "var(--shadow-print)",
        dialog: "var(--shadow-dialog)",
        focus: "var(--shadow-focus)",
      },
      maxWidth: {
        content: "var(--content-max)",
        form: "560px",
        measure: "64ch",
      },
      minHeight: {
        row: "var(--row-h)",
      },
      transitionDuration: {
        instant: "var(--dur-instant)",
        fast: "var(--dur-fast)",
        slow: "var(--dur-slow)",
      },
      transitionTimingFunction: {
        brand: "var(--ease)",
        "brand-out": "var(--ease-out)",
      },
    },
  },
};

export default config;
