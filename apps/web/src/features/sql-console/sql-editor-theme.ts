import { HighlightStyle, syntaxHighlighting } from "@codemirror/language";
import { EditorView } from "@codemirror/view";
import { tags } from "@lezer/highlight";

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
      color: "var(--ink-faint)",
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
      { tag: tags.number, color: "var(--lagoon)" },
      { tag: tags.comment, color: "var(--ink-faint)", fontStyle: "italic" },
    ],
    { themeType: "light" },
  ),
);
