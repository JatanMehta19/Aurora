// --- element refs (the DOM contract from Stage 1) ---
const editor   = document.querySelector("#editor");
const runBtn   = document.querySelector("#run");
const outputEl = document.querySelector("#output");
const statusEl = document.querySelector("#status");
const examplesEl = document.querySelector("#examples");

function setStatus(msg) { statusEl.textContent = msg; }

// --- load Aurora into Pyodide's in-memory filesystem ---
// All 7 must be written before the first import: importing `aurora` pulls in
// `src`, whose __init__.py eagerly imports all five submodules.
const FILES = [
  "aurora.py",
  "src/__init__.py", "src/lexer.py", "src/ast_nodes.py",
  "src/parser.py", "src/environment.py", "src/interpreter.py",
];

async function loadAurora() {
  pyodide.FS.mkdirTree("/aurora/src");

  for (const path of FILES) {
    const res = await fetch(path);          // relative — no leading slash
    // fetch() does not throw on 404; without this we would write the server's
    // HTML error page into a .py file and get a SyntaxError quoting HTML.
    if (!res.ok) throw new Error(`${path}: ${res.status}`);
    pyodide.FS.writeFile(`/aurora/${path}`, await res.text());
  }

  await pyodide.runPythonAsync(`
import sys
sys.path.insert(0, '/aurora')
from aurora import run_source

def aurora_run(source):
    lines = []
    run_source(source, lines.append)
    return lines
`);

  // Cache the proxy once: pyodide.globals.get() mints a new PyProxy per call,
  // so fetching it per click would leak one Python reference each time.
  auroraRun = pyodide.globals.get("aurora_run");
}

// --- boot ---
let pyodide = null;
let auroraRun = null;

async function boot() {
  try {
    setStatus("Loading Python runtime… (~7 MB, first visit only)");
    const t0 = performance.now();

    pyodide = await loadPyodide();

    setStatus("Loading Aurora…");
    await loadAurora();

    const secs = ((performance.now() - t0) / 1000).toFixed(1);
    setStatus(`Ready — loaded in ${secs}s`);
    runBtn.disabled = false;
  } catch (err) {
    setStatus(`Failed to load: ${err.message}`);
    console.error(err);
  }
}

// --- syntax highlighting (ports gui.py:34-37 and gui.py:127-134) ---
const highlightEl = document.querySelector("#highlight");

const KEYWORDS =
  "Int|Float|String|Bool|List|Map|auto|mut|func|class|if|else|while|for|in|" +
  "return|break|import|print|true|false|null|and|or|not";

// One pass, ordered alternation: the first branch to match at a position wins,
// so a keyword inside a comment or string stays comment/string colored.
const TOKEN_RE = new RegExp(
  "(\\/\\/[^\\n]*)" +                          // 1 comment
  "|(\"[^\"\\\\]*(?:\\\\.[^\"\\\\]*)*\")" +    // 2 string
  "|(\\b\\d+(?:\\.\\d+)?\\b)" +                // 3 number
  "|(\\b(?:" + KEYWORDS + ")\\b)",             // 4 keyword
  "g"
);

const escapeHtml = (s) =>
  s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

function highlight() {
  const src = editor.value;
  let html = "", last = 0, m;

  TOKEN_RE.lastIndex = 0;
  while ((m = TOKEN_RE.exec(src)) !== null) {
    html += escapeHtml(src.slice(last, m.index));
    const cls = m[1] ? "tok-cmt" : m[2] ? "tok-str" : m[3] ? "tok-num" : "tok-kw";
    html += `<span class="${cls}">${escapeHtml(m[0])}</span>`;
    last = m.index + m[0].length;
  }
  html += escapeHtml(src.slice(last));

  // Safe: every character of `src` went through escapeHtml; the only markup is
  // the <span> tags built above. The trailing "\n" keeps a final empty line
  // from collapsing, which would shift the overlay against the textarea.
  highlightEl.innerHTML = html + "\n";
}

// --- rendering (mirrors gui.py:153-160) ---
function render(lines) {
  outputEl.textContent = "";

  if (lines.length === 0) {
    const span = document.createElement("span");
    span.className = "info";
    span.textContent = "(no output)";
    outputEl.appendChild(span);
  } else {
    for (const line of lines) {
      const span = document.createElement("span");
      // Same substring test as gui.py:155 — every Aurora error format
      // contains "Error" ([Line N] Lexer Error:, Parse Error:, Runtime Error:).
      if (line.includes("Error")) span.className = "error";
      // textContent, never innerHTML: program output is untrusted text.
      span.textContent = line + "\n";
      outputEl.appendChild(span);
    }
  }

  setStatus(`Done — ${lines.length} line(s) of output`);
}

// --- running ---
async function run() {
  if (!auroraRun) return;

  setStatus("Running…");
  // JS is single-threaded and auroraRun() blocks it, so without yielding once
  // the browser never repaints and "Running…" would never be visible.
  await new Promise(r => setTimeout(r, 0));

  try {
    const proxy = auroraRun(editor.value);
    const lines = proxy.toJs();
    proxy.destroy();               // release the Python list
    render(lines);
  } catch (err) {
    console.error(err);
    setStatus("Internal error — see console");
  }
}

// --- examples (labels and order from gui.py:18-23) ---
const EXAMPLES = [
  ["1 Hello World", "hello"],        ["2 Data Types", "datatypes"],
  ["3 Control Flow", "control"],     ["4 Functions & Recursion", "functions"],
  ["5 Classes", "classes"],          ["6 Error Handling", "errors"],
  ["7 FizzBuzz", "fizzbuzz"],        ["8 Lists & Maps", "collections"],
  ["9 String Methods", "strings"],   ["10 Loops & Ranges", "loops"],
  ["11 Nested Data", "nested"],      ["12 Mutability", "mutability"],
];

const DEFAULT_EXAMPLE = "functions";   // shows types, a return type, recursion

function populateExamples() {
  for (const [label, name] of EXAMPLES) {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = label;
    examplesEl.appendChild(opt);
  }
}

async function loadExample(name, { quiet = false } = {}) {
  const res = await fetch(`examples/${name}.aur`);   // relative — no leading slash
  if (!res.ok) throw new Error(`examples/${name}.aur: ${res.status}`);
  editor.value = await res.text();
  highlight();                  // setting .value does not fire an input event
  outputEl.textContent = "";
  const label = (EXAMPLES.find(([, n]) => n === name) || [name])[0];
  if (!quiet) setStatus(`Loaded: ${label}`);
}

// --- wiring ---
runBtn.addEventListener("click", run);

editor.addEventListener("input", highlight);

// The two layers scroll independently, so keep the overlay pinned to the
// textarea's scroll position.
editor.addEventListener("scroll", () => {
  highlightEl.scrollTop  = editor.scrollTop;
  highlightEl.scrollLeft = editor.scrollLeft;
});

document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault();
    if (!runBtn.disabled) run();
  }
});

examplesEl.addEventListener("change", (e) => {
  loadExample(e.target.value).catch((err) => {
    console.error(err);
    setStatus(`Failed to load example: ${err.message}`);
  });
});

// Populate and show the default example immediately, so the editor has content
// while Pyodide downloads in the background. `quiet` keeps this from
// overwriting boot()'s loading status.
populateExamples();
examplesEl.value = DEFAULT_EXAMPLE;
loadExample(DEFAULT_EXAMPLE, { quiet: true }).catch((err) => console.error(err));

boot();