"""
Generador de Documentación HTML Totalmente Independiente y Modular.
Crea portales 100% aislados y autónomos:
  1. 'guia_testers.html': Exclusivo para Evaluadores y Testers (totalmente aislado).
  2. 'manual_usuario.html': Exclusivo para Usuarios Finales (totalmente aislado).
  3. 'documentacion.html' / 'docs/index.html': Portal Técnico, Arquitectura, DevOps y Desarrollo.

Cada archivo opera en modo offline, con buscador en vivo, tabla de contenidos dinámica (TOC),
resaltado de sintaxis, alternador de temas claro/oscuro y sin dependencias cruzadas indeseadas.
"""

import os
import sys
import json
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")

# Rutas de los archivos Markdown
MD_FILES = {
    "testers": os.path.join(DOCS_DIR, "GUIA_PARA_TESTERS.md"),
    "usuario": os.path.join(DOCS_DIR, "MANUAL_USUARIO_COMUN.md"),
    "tecnico": os.path.join(DOCS_DIR, "MANUAL_TECNICO_Y_FORENSE.md"),
    "arquitectura": os.path.join(DOCS_DIR, "ARQUITECTURA_Y_ESTRUCTURA.md"),
    "compilacion": os.path.join(DOCS_DIR, "COMPILACION_Y_DISTRIBUCION.md"),
    "desarrollo": os.path.join(DOCS_DIR, "MANUAL_DESARROLLADOR_Y_PORTING.md"),
    "changelog": os.path.join(DOCS_DIR, "CHANGELOG.md"),
    "readme": os.path.join(PROJECT_ROOT, "README.md")
}


def fetch_or_fallback(url: str, fallback_content: str = "") -> str:
    """Descarga biblioteca JS/CSS para incrustación inline offline."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.read().decode("utf-8")
    except Exception:
        return fallback_content


def read_md(file_key: str) -> str:
    path = MD_FILES.get(file_key, "")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return f"# Archivo no encontrado: {path}"


# =============================================================================
# CSS BASE COMPARTIDO
# =============================================================================
SHARED_CSS = """
:root {
    --bg-body: #0d1117;
    --bg-surface: #161b22;
    --bg-sidebar: #13171e;
    --bg-card: #21262d;
    --border-color: #30363d;
    --text-primary: #e6edf3;
    --text-secondary: #8b949e;
    --text-muted: #6e7681;
    --accent: #58a6ff;
    --accent-hover: #79b8ff;
    --accent-green: #3fb950;
    --accent-gold: #d29922;
    --accent-orange: #db6d28;
    --accent-red: #f85149;
    --code-bg: #11151c;
    --search-highlight: rgba(234, 179, 8, 0.4);
    --header-h: 68px;
    --sidebar-w: 290px;
    --toc-w: 270px;
    --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
}

[data-theme="light"] {
    --bg-body: #f6f8fa;
    --bg-surface: #ffffff;
    --bg-sidebar: #f0f2f5;
    --bg-card: #f6f8fa;
    --border-color: #d0d7de;
    --text-primary: #1f2328;
    --text-secondary: #656d76;
    --text-muted: #8c959f;
    --accent: #0969da;
    --accent-hover: #218bff;
    --accent-green: #1a7f37;
    --accent-gold: #9a6700;
    --accent-orange: #bc4c00;
    --accent-red: #cf222e;
    --code-bg: #f6f8fa;
    --search-highlight: rgba(255, 215, 0, 0.6);
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: var(--font-family);
    background-color: var(--bg-body);
    color: var(--text-primary);
    line-height: 1.6;
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
}

header {
    height: var(--header-h);
    background-color: var(--bg-surface);
    border-bottom: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
    flex-shrink: 0;
    z-index: 100;
}

.brand {
    display: flex;
    align-items: center;
    gap: 12px;
    text-decoration: none;
    color: var(--text-primary);
}

.brand-icon {
    font-size: 28px;
    line-height: 1;
}

.brand-title {
    font-size: 16px;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 8px;
}

.badge-ver {
    background: rgba(88, 166, 255, 0.15);
    color: var(--accent);
    border: 1px solid rgba(88, 166, 255, 0.4);
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 12px;
    text-transform: uppercase;
}

.header-actions {
    display: flex;
    align-items: center;
    gap: 10px;
}

.search-box {
    position: relative;
    display: flex;
    align-items: center;
}

.search-input {
    background-color: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 7px 12px 7px 32px;
    color: var(--text-primary);
    font-size: 13px;
    width: 230px;
    transition: all 0.2s ease;
}

.search-input:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.2);
    width: 300px;
}

.search-icon {
    position: absolute;
    left: 10px;
    font-size: 13px;
    color: var(--text-muted);
    pointer-events: none;
}

.btn-header {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    padding: 7px 12px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 6px;
    transition: all 0.2s;
}

.btn-header:hover {
    background-color: var(--border-color);
}

.app-container {
    display: flex;
    flex: 1;
    overflow: hidden;
    position: relative;
}

.content-area {
    flex: 1;
    overflow-y: auto;
    padding: 36px 48px;
    scroll-behavior: smooth;
}

.markdown-body {
    max-width: 940px;
    margin: 0 auto;
}

.toc-panel {
    width: var(--toc-w);
    background-color: var(--bg-surface);
    border-right: 1px solid var(--border-color);
    padding: 20px 16px;
    overflow-y: auto;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.toc-title {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--text-muted);
    letter-spacing: 0.5px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border-color);
}

.toc-list {
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 3px;
}

.toc-link {
    color: var(--text-secondary);
    text-decoration: none;
    font-size: 12px;
    line-height: 1.4;
    padding: 5px 8px;
    border-radius: 4px;
    display: block;
    transition: all 0.15s;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.toc-link:hover {
    color: var(--text-primary);
    background-color: var(--bg-card);
}

.toc-link.depth-3 {
    padding-left: 18px;
    font-size: 11.5px;
}

/* Tipografía y bloques Markdown */
.markdown-body h1 {
    font-size: 26px;
    font-weight: 700;
    margin-bottom: 16px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--border-color);
    color: var(--text-primary);
}

.markdown-body h2 {
    font-size: 20px;
    font-weight: 700;
    margin-top: 32px;
    margin-bottom: 14px;
    padding-bottom: 6px;
    border-bottom: 1px solid rgba(48, 54, 61, 0.5);
    color: var(--text-primary);
}

.markdown-body h3 {
    font-size: 16px;
    font-weight: 600;
    margin-top: 24px;
    margin-bottom: 10px;
    color: var(--accent);
}

.markdown-body p {
    margin-bottom: 16px;
    color: var(--text-primary);
    line-height: 1.7;
}

.markdown-body ul, .markdown-body ol {
    margin-bottom: 18px;
    padding-left: 24px;
}

.markdown-body li {
    margin-bottom: 6px;
    line-height: 1.6;
}

.markdown-body code {
    font-family: var(--font-mono);
    background-color: var(--code-bg);
    border: 1px solid var(--border-color);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 12.5px;
    color: #ff7b72;
}

.markdown-body pre {
    background-color: var(--code-bg);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 16px;
    overflow-x: auto;
    margin-bottom: 20px;
    position: relative;
}

.markdown-body pre code {
    background-color: transparent;
    border: none;
    padding: 0;
    font-size: 12.5px;
    color: var(--text-primary);
}

.copy-btn {
    position: absolute;
    top: 8px;
    right: 8px;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    font-size: 11px;
    padding: 4px 8px;
    border-radius: 4px;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.2s;
}

pre:hover .copy-btn { opacity: 1; }

.markdown-body table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 24px;
    font-size: 13px;
}

.markdown-body th, .markdown-body td {
    border: 1px solid var(--border-color);
    padding: 10px 14px;
    text-align: left;
}

.markdown-body th {
    background-color: var(--bg-card);
    font-weight: 600;
}

.markdown-body tr:nth-child(even) {
    background-color: rgba(255, 255, 255, 0.02);
}

.alert-box {
    padding: 14px 16px;
    margin-bottom: 18px;
    border-radius: 6px;
    border-left: 4px solid;
    background-color: var(--bg-card);
}

.alert-box.caution { border-left-color: var(--accent-red); background-color: rgba(248, 81, 73, 0.08); }
.alert-box.warning { border-left-color: var(--accent-orange); background-color: rgba(219, 109, 40, 0.08); }
.alert-box.tip { border-left-color: var(--accent-green); background-color: rgba(63, 185, 80, 0.08); }
.alert-box.note { border-left-color: var(--accent); background-color: rgba(88, 166, 255, 0.08); }

.alert-title {
    font-weight: 700;
    font-size: 12.5px;
    text-transform: uppercase;
    margin-bottom: 6px;
}

.alert-box.caution .alert-title { color: var(--accent-red); }
.alert-box.warning .alert-title { color: var(--accent-orange); }
.alert-box.tip .alert-title { color: var(--accent-green); }
.alert-box.note .alert-title { color: var(--accent); }

mark.search-match {
    background-color: var(--search-highlight);
    color: inherit;
    padding: 1px 3px;
    border-radius: 2px;
    font-weight: bold;
}

@media print {
    header, .toc-panel, .sidebar-tabs, .copy-btn { display: none !important; }
    body, .content-area {
        overflow: visible !important;
        height: auto !important;
        background: white !important;
        color: black !important;
    }
}

@media (max-width: 1024px) {
    .toc-panel { display: none; }
    .content-area { padding: 24px 20px; }
}
"""


# =============================================================================
# 1. PÁGINA TOTALMENTE INDEPENDIENTE (Guía para Testers o Manual de Usuario)
# =============================================================================
def build_standalone_page(
    doc_key: str,
    page_title: str,
    badge_text: str,
    subtitle_text: str,
    icon_emoji: str,
    out_files: list,
    marked_js: str,
    highlight_js: str
):
    """Construye un portal HTML 100% aislado e independiente para un documento específico."""
    md_content = read_md(doc_key)

    html = f"""<!DOCTYPE html>
<html lang="es" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title} - Forensic Data Recovery Suite</title>
    <style>
        {SHARED_CSS}
    </style>
</head>
<body>

    <header>
        <div class="brand">
            <span class="brand-icon">{icon_emoji}</span>
            <div>
                <div class="brand-title">
                    {page_title}
                    <span class="badge-ver">{badge_text}</span>
                </div>
                <div style="font-size: 11px; color: var(--text-muted); font-weight: 500;">{subtitle_text}</div>
            </div>
        </div>

        <div class="header-actions">
            <div class="search-box">
                <span class="search-icon">🔍</span>
                <input type="text" id="globalSearch" class="search-input" placeholder="Buscar en el documento...">
            </div>

            <button class="btn-header" id="themeToggle" title="Cambiar tema de color">
                <span id="themeIcon">☀️</span> Tema
            </button>

            <button class="btn-header" id="printBtn" title="Imprimir o exportar como PDF">
                🖨️ Imprimir
            </button>
        </div>
    </header>

    <div class="app-container">
        <!-- Panel Izquierdo: Tabla de Contenidos Interactiva -->
        <aside class="toc-panel" id="tocPanel">
            <div class="toc-title">Índice del Documento</div>
            <ul class="toc-list" id="tocList"></ul>
        </aside>

        <!-- Área Central de Lectura -->
        <main class="content-area" id="contentArea">
            <div class="markdown-body" id="docContent"></div>
        </main>
    </div>

    <script>
        {marked_js}
    </script>
    <script>
        {highlight_js}
    </script>

    <script id="raw-markdown" type="text/plain">
{md_content}
    </script>

    <script>
        const rawMarkdown = document.getElementById('raw-markdown').textContent;
        let originalHtml = "";

        if (typeof marked !== 'undefined') {{
            marked.setOptions({{
                gfm: true,
                breaks: false,
                highlight: function(code, lang) {{
                    if (typeof hljs !== 'undefined' && lang && hljs.getLanguage(lang)) {{
                        return hljs.highlight(code, {{ language: lang }}).value;
                    }}
                    return typeof hljs !== 'undefined' ? hljs.highlightAuto(code).value : code;
                }}
            }});
        }}

        function parseAlerts(html) {{
            return html
                .replace(/<blockquote>\\s*<p>\\s*\\[!NOTE\\]\\s*([\\s\\S]*?)<\\/p>\\s*<\\/blockquote>/gi, 
                    '<div class="alert-box note"><div class="alert-title">ℹ️ NOTA INFORMATIVA</div><p>$1</p></div>')
                .replace(/<blockquote>\\s*<p>\\s*\\[!TIP\\]\\s*([\\s\\S]*?)<\\/p>\\s*<\\/blockquote>/gi, 
                    '<div class="alert-box tip"><div class="alert-title">💡 CONSEJO ÚTIL</div><p>$1</p></div>')
                .replace(/<blockquote>\\s*<p>\\s*\\[!IMPORTANT\\]\\s*([\\s\\S]*?)<\\/p>\\s*<\\/blockquote>/gi, 
                    '<div class="alert-box warning"><div class="alert-title">⚠️ IMPORTANTE</div><p>$1</p></div>')
                .replace(/<blockquote>\\s*<p>\\s*\\[!WARNING\\]\\s*([\\s\\S]*?)<\\/p>\\s*<\\/blockquote>/gi, 
                    '<div class="alert-box warning"><div class="alert-title">⚠️ ADVERTENCIA</div><p>$1</p></div>')
                .replace(/<blockquote>\\s*<p>\\s*\\[!CAUTION\\]\\s*([\\s\\S]*?)<\\/p>\\s*<\\/blockquote>/gi, 
                    '<div class="alert-box caution"><div class="alert-title">🛑 ATENCIÓN CRÍTICA</div><p>$1</p></div>');
        }}

        function renderDocument() {{
            const contentEl = document.getElementById('docContent');
            let parsed = marked.parse(rawMarkdown);
            parsed = parseAlerts(parsed);
            originalHtml = parsed;
            contentEl.innerHTML = parsed;

            contentEl.querySelectorAll('pre').forEach(pre => {{
                const btn = document.createElement('button');
                btn.className = 'copy-btn';
                btn.innerText = 'Copiar';
                btn.onclick = () => {{
                    const code = pre.querySelector('code') ? pre.querySelector('code').innerText : pre.innerText;
                    navigator.clipboard.writeText(code);
                    btn.innerText = '¡Copiado!';
                    setTimeout(() => btn.innerText = 'Copiar', 1500);
                }};
                pre.appendChild(btn);
            }});

            buildTableOfContents();
        }}

        function buildTableOfContents() {{
            const tocList = document.getElementById('tocList');
            tocList.innerHTML = '';
            const contentEl = document.getElementById('docContent');
            const headings = contentEl.querySelectorAll('h1, h2, h3');

            headings.forEach((h, index) => {{
                const id = `heading-${{index}}`;
                h.id = id;

                const li = document.createElement('li');
                const a = document.createElement('a');
                a.className = `toc-link depth-${{h.tagName.toLowerCase().charAt(1)}}`;
                a.href = `#${{id}}`;
                a.innerText = h.innerText.replace(/^[#\\s]+/, '');
                a.onclick = (e) => {{
                    e.preventDefault();
                    h.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                    history.pushState(null, null, `#${{id}}`);
                }};
                li.appendChild(a);
                tocList.appendChild(li);
            }});
        }}

        function performSearch(query) {{
            const contentEl = document.getElementById('docContent');
            if (!query) {{
                contentEl.innerHTML = originalHtml;
                return;
            }}

            const escaped = query.replace(/[-\\/\\\\^$*+?.()|[\\]{{}}]/g, '\\\\$&');
            const regex = new RegExp(`(${{escaped}})`, 'gi');
            const temp = document.createElement('div');
            temp.innerHTML = originalHtml;

            function highlightTextNodes(node) {{
                if (node.nodeType === 3) {{
                    const val = node.nodeValue;
                    if (val && regex.test(val)) {{
                        const span = document.createElement('span');
                        span.innerHTML = val.replace(regex, '<mark class="search-match">$1</mark>');
                        node.parentNode.replaceChild(span, node);
                    }}
                }} else if (node.nodeType === 1 && node.nodeName !== 'SCRIPT' && node.nodeName !== 'STYLE') {{
                    Array.from(node.childNodes).forEach(highlightTextNodes);
                }}
            }}

            highlightTextNodes(temp);
            contentEl.innerHTML = temp.innerHTML;
        }}

        document.getElementById('globalSearch').addEventListener('input', (e) => {{
            performSearch(e.target.value.trim());
        }});

        const themeBtn = document.getElementById('themeToggle');
        const themeIcon = document.getElementById('themeIcon');
        themeBtn.onclick = () => {{
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            themeIcon.innerText = next === 'dark' ? '☀️' : '🌙';
        }};

        document.getElementById('printBtn').onclick = () => window.print();

        window.addEventListener('DOMContentLoaded', renderDocument);
    </script>
</body>
</html>
"""
    for out_path in out_files:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        rel = os.path.relpath(out_path, PROJECT_ROOT)
        print(f"✓ Creado (Aislado e Independiente): {rel}")


# =============================================================================
# 2. PORTAL TÉCNICO, ARQUITECTURA & CÓDIGO (documentacion.html)
# =============================================================================
def build_technical_portal(out_files: list, marked_js: str, highlight_js: str):
    """Construye el portal exclusivo para técnicos, desarrolladores y DevOps (sin testers ni manual de usuario)."""

    tech_specs = [
        {"id": "tecnico", "title": "Manual Técnico & Forense", "icon": "🔬", "badge": "Avanzado", "file": "tecnico"},
        {"id": "arquitectura", "title": "Arquitectura & Código", "icon": "🏛️", "badge": "Estructura", "file": "arquitectura"},
        {"id": "compilacion", "title": "Compilación & Distribución", "icon": "🔨", "badge": "DevOps", "file": "compilacion"},
        {"id": "desarrollo", "title": "Desarrollador & Porting", "icon": "💻", "badge": "Programadores", "file": "desarrollo"},
        {"id": "changelog", "title": "Registro de Cambios", "icon": "📜", "badge": "v2.5.0", "file": "changelog"},
        {"id": "readme", "title": "README General", "icon": "🛡️", "badge": "Visión Global", "file": "readme"}
    ]

    documents = {}
    for spec in tech_specs:
        documents[spec["id"]] = {
            "id": spec["id"],
            "title": spec["title"],
            "icon": spec["icon"],
            "badge": spec["badge"],
            "markdown": read_md(spec["file"])
        }

    html = f"""<!DOCTYPE html>
<html lang="es" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Documentación Técnica y Arquitectura - Forensic Data Recovery Suite</title>
    <style>
        {SHARED_CSS}

        .sidebar-tabs {{
            width: var(--sidebar-w);
            background-color: var(--bg-sidebar);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            overflow-y: auto;
            flex-shrink: 0;
            padding: 14px 10px;
            gap: 4px;
        }}

        .sidebar-section-title {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            color: var(--text-muted);
            padding: 10px 12px 4px 12px;
            letter-spacing: 0.5px;
        }}

        .tab-btn {{
            background: transparent;
            border: 1px solid transparent;
            color: var(--text-secondary);
            padding: 10px 12px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            text-align: left;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: all 0.15s ease;
        }}

        .tab-btn:hover {{
            background-color: var(--bg-card);
            color: var(--text-primary);
        }}

        .tab-btn.active {{
            background-color: rgba(88, 166, 255, 0.12);
            color: var(--accent);
            border-color: rgba(88, 166, 255, 0.35);
        }}

        .tab-btn-title {{
            display: flex;
            align-items: center;
            gap: 9px;
        }}

        .tab-badge {{
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 10px;
            background-color: var(--bg-card);
            color: var(--text-muted);
            border: 1px solid var(--border-color);
        }}

        .tab-btn.active .tab-badge {{
            background-color: rgba(88, 166, 255, 0.25);
            color: var(--accent);
            border-color: rgba(88, 166, 255, 0.4);
        }}
    </style>
</head>
<body>

    <header>
        <div class="brand">
            <span class="brand-icon">🔬</span>
            <div>
                <div class="brand-title">
                    Forensic Data Recovery Suite
                    <span class="badge-ver">v2.5.0</span>
                </div>
                <div style="font-size: 11px; color: var(--text-muted); font-weight: 500;">Portal Técnico, Arquitectura & Código</div>
            </div>
        </div>

        <div class="header-actions">
            <div class="search-box">
                <span class="search-icon">🔍</span>
                <input type="text" id="globalSearch" class="search-input" placeholder="Buscar en la documentación...">
            </div>

            <button class="btn-header" id="themeToggle" title="Cambiar tema">
                <span id="themeIcon">☀️</span> Tema
            </button>

            <button class="btn-header" id="printBtn" title="Imprimir o guardar como PDF">
                🖨️ Imprimir
            </button>
        </div>
    </header>

    <div class="app-container">
        <!-- 1. Barra Lateral de Módulos Técnicos -->
        <nav class="sidebar-tabs" id="sidebarNav">
            <div class="sidebar-section-title">Módulos Técnicos & Código</div>
        </nav>

        <!-- 2. Área Central de Contenido -->
        <main class="content-area" id="contentArea">
            <div class="markdown-body" id="docContent"></div>
        </main>

        <!-- 3. Panel Lateral Derecho: Tabla de Contenidos -->
        <aside class="toc-panel" id="tocPanel">
            <div class="toc-title">Índice del Módulo</div>
            <ul class="toc-list" id="tocList"></ul>
        </aside>
    </div>

    <script>
        {marked_js}
    </script>
    <script>
        {highlight_js}
    </script>

    <script id="doc-data" type="application/json">
        {json.dumps(documents, ensure_ascii=False)}
    </script>

    <script>
        const DOC_MAP = JSON.parse(document.getElementById('doc-data').textContent);
        let currentDocId = "tecnico";
        let originalHtmlCache = {{}};

        if (typeof marked !== 'undefined') {{
            marked.setOptions({{
                gfm: true,
                breaks: false,
                highlight: function(code, lang) {{
                    if (typeof hljs !== 'undefined' && lang && hljs.getLanguage(lang)) {{
                        return hljs.highlight(code, {{ language: lang }}).value;
                    }}
                    return typeof hljs !== 'undefined' ? hljs.highlightAuto(code).value : code;
                }}
            }});
        }}

        function parseAlerts(html) {{
            return html
                .replace(/<blockquote>\\s*<p>\\s*\\[!NOTE\\]\\s*([\\s\\S]*?)<\\/p>\\s*<\\/blockquote>/gi, 
                    '<div class="alert-box note"><div class="alert-title">ℹ️ NOTA INFORMATIVA</div><p>$1</p></div>')
                .replace(/<blockquote>\\s*<p>\\s*\\[!TIP\\]\\s*([\\s\\S]*?)<\\/p>\\s*<\\/blockquote>/gi, 
                    '<div class="alert-box tip"><div class="alert-title">💡 CONSEJO ÚTIL</div><p>$1</p></div>')
                .replace(/<blockquote>\\s*<p>\\s*\\[!IMPORTANT\\]\\s*([\\s\\S]*?)<\\/p>\\s*<\\/blockquote>/gi, 
                    '<div class="alert-box warning"><div class="alert-title">⚠️ IMPORTANTE</div><p>$1</p></div>')
                .replace(/<blockquote>\\s*<p>\\s*\\[!WARNING\\]\\s*([\\s\\S]*?)<\\/p>\\s*<\\/blockquote>/gi, 
                    '<div class="alert-box warning"><div class="alert-title">⚠️ ADVERTENCIA</div><p>$1</p></div>')
                .replace(/<blockquote>\\s*<p>\\s*\\[!CAUTION\\]\\s*([\\s\\S]*?)<\\/p>\\s*<\\/blockquote>/gi, 
                    '<div class="alert-box caution"><div class="alert-title">🛑 ATENCIÓN CRÍTICA</div><p>$1</p></div>');
        }}

        function initSidebarTabs() {{
            const nav = document.getElementById('sidebarNav');
            const keys = Object.keys(DOC_MAP);

            keys.forEach(docId => {{
                const d = DOC_MAP[docId];
                const btn = document.createElement('button');
                btn.className = `tab-btn ${{docId === currentDocId ? 'active' : ''}}`;
                btn.id = `tab-btn-${{docId}}`;
                btn.onclick = () => switchTab(docId);

                btn.innerHTML = `
                    <div class="tab-btn-title">
                        <span>${{d.icon}}</span>
                        <span>${{d.title}}</span>
                    </div>
                    <span class="tab-badge">${{d.badge}}</span>
                `;
                nav.appendChild(btn);
            }});
        }}

        function switchTab(docId) {{
            if (!DOC_MAP[docId]) return;
            currentDocId = docId;

            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            const activeBtn = document.getElementById(`tab-btn-${{docId}}`);
            if (activeBtn) activeBtn.classList.add('active');

            const contentEl = document.getElementById('docContent');

            if (!originalHtmlCache[docId]) {{
                let rawHtml = marked.parse(DOC_MAP[docId].markdown);
                rawHtml = parseAlerts(rawHtml);
                originalHtmlCache[docId] = rawHtml;
            }}

            contentEl.innerHTML = originalHtmlCache[docId];

            contentEl.querySelectorAll('pre').forEach(pre => {{
                const btn = document.createElement('button');
                btn.className = 'copy-btn';
                btn.innerText = 'Copiar';
                btn.onclick = () => {{
                    const code = pre.querySelector('code') ? pre.querySelector('code').innerText : pre.innerText;
                    navigator.clipboard.writeText(code);
                    btn.innerText = '¡Copiado!';
                    setTimeout(() => btn.innerText = 'Copiar', 1500);
                }};
                pre.appendChild(btn);
            }});

            buildTableOfContents();
            document.getElementById('contentArea').scrollTop = 0;

            const searchVal = document.getElementById('globalSearch').value.trim();
            if (searchVal) performSearch(searchVal);
        }}

        function buildTableOfContents() {{
            const tocList = document.getElementById('tocList');
            tocList.innerHTML = '';
            const contentEl = document.getElementById('docContent');
            const headings = contentEl.querySelectorAll('h1, h2, h3');

            headings.forEach((h, index) => {{
                const id = `heading-${{index}}`;
                h.id = id;

                const li = document.createElement('li');
                const a = document.createElement('a');
                a.className = `toc-link depth-${{h.tagName.toLowerCase().charAt(1)}}`;
                a.href = `#${{id}}`;
                a.innerText = h.innerText.replace(/^[#\\s]+/, '');
                a.onclick = (e) => {{
                    e.preventDefault();
                    h.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                    history.pushState(null, null, `#${{id}}`);
                }};
                li.appendChild(a);
                tocList.appendChild(li);
            }});
        }}

        function performSearch(query) {{
            const contentEl = document.getElementById('docContent');
            if (!query) {{
                contentEl.innerHTML = originalHtmlCache[currentDocId] || contentEl.innerHTML;
                return;
            }}

            const raw = originalHtmlCache[currentDocId] || contentEl.innerHTML;
            const escaped = query.replace(/[-\\/\\\\^$*+?.()|[\\]{{}}]/g, '\\\\$&');
            const regex = new RegExp(`(${{escaped}})`, 'gi');
            const temp = document.createElement('div');
            temp.innerHTML = raw;

            function highlightTextNodes(node) {{
                if (node.nodeType === 3) {{
                    const val = node.nodeValue;
                    if (val && regex.test(val)) {{
                        const span = document.createElement('span');
                        span.innerHTML = val.replace(regex, '<mark class="search-match">$1</mark>');
                        node.parentNode.replaceChild(span, node);
                    }}
                }} else if (node.nodeType === 1 && node.nodeName !== 'SCRIPT' && node.nodeName !== 'STYLE') {{
                    Array.from(node.childNodes).forEach(highlightTextNodes);
                }}
            }}

            highlightTextNodes(temp);
            contentEl.innerHTML = temp.innerHTML;
        }}

        document.getElementById('globalSearch').addEventListener('input', (e) => {{
            performSearch(e.target.value.trim());
        }});

        const themeBtn = document.getElementById('themeToggle');
        const themeIcon = document.getElementById('themeIcon');
        themeBtn.onclick = () => {{
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            themeIcon.innerText = next === 'dark' ? '☀️' : '🌙';
        }};

        document.getElementById('printBtn').onclick = () => window.print();

        window.addEventListener('DOMContentLoaded', () => {{
            initSidebarTabs();
            switchTab('tecnico');
        }});
    </script>
</body>
</html>
"""
    for out_path in out_files:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        rel = os.path.relpath(out_path, PROJECT_ROOT)
        print(f"✓ Creado (Portal Técnico Exclusivo): {rel}")


def build_all():
    print("=" * 70)
    print(" 📚 GENERADOR DE PORTALES HTML TOTALMENTE INDEPENDIENTES")
    print("=" * 70)

    marked_js = fetch_or_fallback("https://cdn.jsdelivr.net/npm/marked/marked.min.js", "/* Marked fallback */")
    highlight_js = fetch_or_fallback("https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js", "/* Highlight fallback */")

    # 1. Guía para Testers (Totalmente independiente, cero enlaces externos)
    build_standalone_page(
        doc_key="testers",
        page_title="Guía Oficial para Evaluadores (Beta Testers)",
        badge_text="BETA 24H",
        subtitle_text="Pautas de evaluación, expectativas reales de recuperación y feedback",
        icon_emoji="🧪",
        out_files=[
            os.path.join(PROJECT_ROOT, "guia_testers.html"),
            os.path.join(DOCS_DIR, "guia_testers.html")
        ],
        marked_js=marked_js,
        highlight_js=highlight_js
    )

    # 2. Manual de Usuario (Totalmente independiente, cero enlaces externos)
    build_standalone_page(
        doc_key="usuario",
        page_title="Manual de Usuario Oficial",
        badge_text="GUÍA COMPLETA",
        subtitle_text="Instrucciones paso a paso, controles y preguntas frecuentes",
        icon_emoji="📖",
        out_files=[
            os.path.join(PROJECT_ROOT, "manual_usuario.html"),
            os.path.join(DOCS_DIR, "manual_usuario.html")
        ],
        marked_js=marked_js,
        highlight_js=highlight_js
    )

    # 3. Documentación Técnica (Sin testers ni manual de usuario, puramente técnico y de código)
    build_technical_portal(
        out_files=[
            os.path.join(PROJECT_ROOT, "documentacion.html"),
            os.path.join(DOCS_DIR, "index.html"),
            os.path.join(DOCS_DIR, "documentacion.html")
        ],
        marked_js=marked_js,
        highlight_js=highlight_js
    )

    print("\n🎉 ¡Todos los portales han sido generados de forma 100% independiente!")


if __name__ == "__main__":
    build_all()
