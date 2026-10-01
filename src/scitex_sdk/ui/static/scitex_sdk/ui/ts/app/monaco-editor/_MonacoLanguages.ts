/**
 * Monaco Languages — scitex-ui
 * Language registration (LaTeX, BibTeX) and generic LaTeX snippet completions.
 * Like Emacs major-modes: the editor knows how to highlight each language.
 */

// ── LaTeX ────────────────────────────────────────────────────────────

export function registerLatexLanguage(monaco: any): void {
  if (monaco.languages.getLanguages().find((l: any) => l.id === "latex")) {
    return;
  }

  monaco.languages.register({
    id: "latex",
    extensions: [".tex", ".sty", ".cls", ".ltx"],
  });

  monaco.languages.setLanguageConfiguration("latex", {
    comments: { lineComment: "%" },
    brackets: [
      ["{", "}"],
      ["[", "]"],
      ["(", ")"],
      ["\\begin{", "\\end{"],
    ],
    autoClosingPairs: [
      { open: "{", close: "}" },
      { open: "[", close: "]" },
      { open: "(", close: ")" },
      { open: "$", close: "$" },
      { open: "`", close: "'" },
      { open: "\\begin{", close: "}", notIn: ["string", "comment"] },
    ],
    surroundingPairs: [
      { open: "{", close: "}" },
      { open: "[", close: "]" },
      { open: "(", close: ")" },
      { open: "$", close: "$" },
    ],
  });

  // Comprehensive Monarch tokenizer (uses .latex suffix for theme rules)
  monaco.languages.setMonarchTokensProvider("latex", {
    defaultToken: "",
    tokenPostfix: ".latex",

    environments: [
      "document",
      "abstract",
      "equation",
      "align",
      "gather",
      "multline",
      "figure",
      "table",
      "tabular",
      "itemize",
      "enumerate",
      "description",
      "verbatim",
      "lstlisting",
      "quote",
      "quotation",
      "verse",
      "center",
      "flushleft",
      "flushright",
      "minipage",
      "array",
      "matrix",
      "cases",
      "theorem",
      "lemma",
      "proof",
      "definition",
      "corollary",
      "remark",
    ],

    tokenizer: {
      root: [
        [/%.*$/, "comment"],
        [/\$\$/, { token: "string.math", next: "@displayMath" }],
        [/\$/, { token: "string.math", next: "@inlineMath" }],
        [
          /(\\begin)(\{)([a-zA-Z*]+)(\})/,
          [
            "keyword.control",
            "delimiter.curly",
            "type.identifier",
            "delimiter.curly",
          ],
        ],
        [
          /(\\end)(\{)([a-zA-Z*]+)(\})/,
          [
            "keyword.control",
            "delimiter.curly",
            "type.identifier",
            "delimiter.curly",
          ],
        ],
        [
          /\\(section|subsection|subsubsection|paragraph|chapter|part)\b/,
          "keyword.section",
        ],
        [/\\[a-zA-Z@]+\*?/, "keyword"],
        [/\{/, "delimiter.curly"],
        [/\}/, "delimiter.curly"],
        [/\[/, "delimiter.square"],
        [/\]/, "delimiter.square"],
        [/\d+/, "number"],
        [/[&~^_]/, "operator"],
      ],
      displayMath: [
        [/\$\$/, { token: "string.math", next: "@pop" }],
        [/\\[a-zA-Z@]+/, "keyword.math"],
        [/./, "string.math"],
      ],
      inlineMath: [
        [/\$/, { token: "string.math", next: "@pop" }],
        [/\\[a-zA-Z@]+/, "keyword.math"],
        [/./, "string.math"],
      ],
    },
  });
}

// ── BibTeX ───────────────────────────────────────────────────────────

export function registerBibtexLanguage(monaco: any): void {
  if (monaco.languages.getLanguages().find((l: any) => l.id === "bibtex")) {
    return;
  }

  monaco.languages.register({ id: "bibtex", extensions: [".bib"] });
  monaco.languages.setMonarchTokensProvider("bibtex", {
    defaultToken: "",
    tokenPostfix: ".bibtex",
    tokenizer: {
      root: [
        [/%.*$/, "comment"],
        [/@[a-zA-Z]+/, "keyword"],
        [/\{/, "delimiter.curly"],
        [/\}/, "delimiter.curly"],
        [/=/, "operator"],
        [/"[^"]*"/, "string"],
        [/\d+/, "number"],
      ],
    },
  });
}

// ── LaTeX snippet completions (generic, not citation-specific) ──────

export function registerLatexSnippetProvider(monaco: any): void {
  monaco.languages.registerCompletionItemProvider("latex", {
    triggerCharacters: ["\\"],
    provideCompletionItems: (model: any, position: any) => {
      const word = model.getWordUntilPosition(position);
      const range = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endColumn: word.endColumn,
      };

      const snippet =
        monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet;
      const kw = monaco.languages.CompletionItemKind.Keyword;

      const suggestions = [
        {
          label: "\\documentclass",
          kind: kw,
          insertText: "\\documentclass{article}",
          documentation: "Document class",
        },
        {
          label: "\\begin",
          kind: kw,
          insertText:
            "\\begin{${1:environment}}\n\t$0\n\\end{${1:environment}}",
          insertTextRules: snippet,
          documentation: "Begin environment",
        },
        {
          label: "\\end",
          kind: kw,
          insertText: "\\end{${1:environment}}",
          insertTextRules: snippet,
          documentation: "End environment",
        },
        {
          label: "\\section",
          kind: kw,
          insertText: "\\section{$0}",
          insertTextRules: snippet,
          documentation: "Section",
        },
        {
          label: "\\subsection",
          kind: kw,
          insertText: "\\subsection{$0}",
          insertTextRules: snippet,
          documentation: "Subsection",
        },
        {
          label: "\\subsubsection",
          kind: kw,
          insertText: "\\subsubsection{$0}",
          insertTextRules: snippet,
          documentation: "Subsubsection",
        },
        {
          label: "\\textbf",
          kind: kw,
          insertText: "\\textbf{$0}",
          insertTextRules: snippet,
          documentation: "Bold text",
        },
        {
          label: "\\textit",
          kind: kw,
          insertText: "\\textit{$0}",
          insertTextRules: snippet,
          documentation: "Italic text",
        },
        {
          label: "\\emph",
          kind: kw,
          insertText: "\\emph{$0}",
          insertTextRules: snippet,
          documentation: "Emphasized text",
        },
        {
          label: "\\texttt",
          kind: kw,
          insertText: "\\texttt{$0}",
          insertTextRules: snippet,
          documentation: "Typewriter text",
        },
        {
          label: "\\[",
          kind: kw,
          insertText: "\\[\n\t$0\n\\]",
          insertTextRules: snippet,
          documentation: "Display math",
        },
        {
          label: "\\(",
          kind: kw,
          insertText: "\\($0\\)",
          insertTextRules: snippet,
          documentation: "Inline math",
        },
        {
          label: "\\equation",
          kind: kw,
          insertText: "\\begin{equation}\n\t$0\n\\end{equation}",
          insertTextRules: snippet,
          documentation: "Equation environment",
        },
        {
          label: "\\figure",
          kind: kw,
          insertText:
            "\\begin{figure}[htbp]\n\t\\centering\n\t\\includegraphics[width=0.8\\textwidth]{$1}\n\t\\caption{$2}\n\t\\label{fig:$3}\n\\end{figure}",
          insertTextRules: snippet,
          documentation: "Figure environment",
        },
        {
          label: "\\table",
          kind: kw,
          insertText:
            "\\begin{table}[htbp]\n\t\\centering\n\t\\caption{$1}\n\t\\label{tab:$2}\n\t\\begin{tabular}{$3}\n\t\t$0\n\t\\end{tabular}\n\\end{table}",
          insertTextRules: snippet,
          documentation: "Table environment",
        },
        {
          label: "\\cite",
          kind: kw,
          insertText: "\\cite{$0}",
          insertTextRules: snippet,
          documentation: "Citation",
        },
        {
          label: "\\ref",
          kind: kw,
          insertText: "\\ref{$0}",
          insertTextRules: snippet,
          documentation: "Reference",
        },
        {
          label: "\\label",
          kind: kw,
          insertText: "\\label{$0}",
          insertTextRules: snippet,
          documentation: "Label",
        },
        {
          label: "\\itemize",
          kind: kw,
          insertText: "\\begin{itemize}\n\t\\item $0\n\\end{itemize}",
          insertTextRules: snippet,
          documentation: "Itemize list",
        },
        {
          label: "\\enumerate",
          kind: kw,
          insertText: "\\begin{enumerate}\n\t\\item $0\n\\end{enumerate}",
          insertTextRules: snippet,
          documentation: "Enumerate list",
        },
        {
          label: "\\item",
          kind: kw,
          insertText: "\\item $0",
          insertTextRules: snippet,
          documentation: "List item",
        },
      ];

      return { suggestions: suggestions.map((s) => ({ ...s, range })) };
    },
  });
}

// ── Register all custom languages ───────────────────────────────────

export function registerCustomLanguages(monaco: any): void {
  registerLatexLanguage(monaco);
  registerBibtexLanguage(monaco);
  registerLatexSnippetProvider(monaco);
}
