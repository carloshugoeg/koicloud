import { HighlightStyle, syntaxHighlighting } from "@codemirror/language";
import { EditorView } from "@codemirror/view";
import { tags } from "@lezer/highlight";

/** Accessible name for the CodeMirror contenteditable textbox. */
export const sqlEditorA11y = EditorView.contentAttributes.of({
  "aria-label": "Consulta SQL",
});

export const sqlEditorChrome = EditorView.theme(
  {
    "&": {
      backgroundColor: "var(--paper)",
      color: "var(--ink)",
      fontFamily: "var(--font-mono)",
      fontSize: "13px",
    },
    ".cm-content": {
      caretColor: "var(--ink)",
      lineHeight: "20px",
      padding: "16px 0",
    },
    ".cm-cursor, .cm-dropCursor": {
      borderLeftColor: "var(--ink)",
    },
    "&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection": {
      backgroundColor: "var(--turquoise-100)",
    },
    ".cm-activeLine": {
      backgroundColor: "var(--bone)",
    },
    ".cm-gutters": {
      backgroundColor: "var(--bone-sunk)",
      border: "none",
      /* ink-faint fails AA on bone; gutters are readable UI text */
      color: "var(--ink-muted)",
    },
    ".cm-activeLineGutter": {
      backgroundColor: "var(--bone)",
    },
  },
  { dark: false },
);

export const sqlSyntaxHighlight = syntaxHighlighting(
  HighlightStyle.define(
    [
      { tag: [tags.name, tags.variableName], color: "var(--ink)" },
      {
        tag: tags.function(tags.variableName),
        color: "var(--ink)",
        fontWeight: "500",
      },
      { tag: tags.keyword, color: "var(--turquoise-700)", fontWeight: "500" },
      { tag: tags.string, color: "var(--green-700)" },
      /* lagoon / ink-faint are not paragraph colors on bone (AA) */
      { tag: tags.number, color: "var(--turquoise-700)" },
      { tag: tags.comment, color: "var(--ink-muted)", fontStyle: "italic" },
    ],
    { themeType: "light" },
  ),
);
