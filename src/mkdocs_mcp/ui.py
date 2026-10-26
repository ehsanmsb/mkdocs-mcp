"""Small, dependency-free browser pages for the MCP endpoint."""

from __future__ import annotations

from html import escape
from urllib.parse import urlsplit

from .config import Settings
from .context import AppContext

_STYLE = """
:root{color-scheme:dark;font-family:Inter,ui-sans-serif,system-ui,sans-serif}
*{box-sizing:border-box}body{margin:0;min-height:100vh;color:#e9f0ff;background:
radial-gradient(circle at 18% 12%,#173867 0,transparent 32%),
radial-gradient(circle at 85% 78%,#392056 0,transparent 34%),#0a1020}
main{max-width:880px;margin:auto;padding:clamp(32px,7vw,88px) 24px}
.eyebrow{color:#8fb8ff;font-size:.8rem;font-weight:700;letter-spacing:.2em;text-transform:uppercase}
h1{font-size:clamp(2.4rem,6vw,4.5rem);line-height:1.08;margin:18px 0}
p{color:#b4c1d8;line-height:1.7}a{color:#9cc5ff}
.lead{max-width:650px;font-size:1.1rem}.panel{background:#141e33;border:1px solid #304061;
border-radius:20px;padding:28px;margin-top:28px;box-shadow:0 18px 60px #050a1680}
.row{display:flex;gap:14px;align-items:center;flex-wrap:wrap}.status{display:inline-flex;
align-items:center;gap:8px;border:1px solid #42665e;border-radius:99px;padding:7px 12px;
font-size:.85rem;color:#a8f4cf}.status.wait{border-color:#806544;color:#ffd79b}
.dot{width:8px;height:8px;border-radius:50%;background:currentColor}
.stats{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:22px}
.stat{padding:18px;background:#0d1628;border-radius:12px}
.stat strong{display:block;font-size:1.7rem}
.stat span{color:#a5b5d0;font-size:.85rem}
code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;word-break:break-all}
.endpoint{display:flex;align-items:center;gap:12px;justify-content:space-between;
background:#0a1223;border:1px solid #344b72;border-radius:12px;padding:14px 16px;margin:16px 0}
button,.button{background:#579bff;color:#081427;border:0;border-radius:9px;padding:10px 15px;
font:inherit;font-weight:700;cursor:pointer;text-decoration:none}button:hover,.button:hover{background:#83b5ff}
.muted{font-size:.88rem}.links{display:flex;gap:18px;flex-wrap:wrap;margin-top:22px}
@media(max-width:520px){.stats{grid-template-columns:1fr}.endpoint{align-items:flex-start;flex-direction:column}}
"""


def _page(title: str, body: str) -> str:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)}</title><style>{_STYLE}</style></head>"
        f"<body><main>{body}</main></body></html>"
    )


def home_page(cfg: Settings, ctx: AppContext) -> str:
    loaded = ctx.store.is_loaded
    status = "Ready" if loaded else "Loading documentation"
    status_class = "" if loaded else " wait"
    site = urlsplit(cfg.base_url)
    docs_link = (
        f'<a href="{escape(cfg.base_url, quote=True)}" target="_blank" rel="noopener noreferrer">'
        "Open documentation ↗</a>"
        if site.scheme in {"http", "https"} and site.netloc
        else ""
    )
    body = f"""
<div class="eyebrow">Documentation · MCP</div>
<h1>{escape(cfg.server_name)}</h1>
<p class="lead">Connect your MCP client to search and read this site's published
documentation. No sign-in is required.</p>
<div class="panel">
  <div class="row"><span class="status{status_class}"><span class="dot"></span>{status}</span>
  <span class="muted">Published MkDocs search index</span></div>
  <div class="stats">
    <div class="stat"><strong>{len(ctx.store.documents)}</strong><span>Pages indexed</span></div>
    <div class="stat"><strong>{len(ctx.store.sections)}</strong>
      <span>Sections searchable</span></div>
  </div>
</div>
<div class="panel">
  <div class="eyebrow">Connection</div>
  <h2>MCP endpoint</h2>
  <div class="endpoint"><code id="endpoint">/mcp</code>
    <button id="copy" type="button">Copy URL</button></div>
  <p class="muted">Use this URL in an MCP client with HTTP transport.
  A browser can show this page, while MCP requests use the same endpoint.</p>
  <div class="links">{docs_link}<a href="/ready">Readiness status</a></div>
</div>
<script>
const endpoint = new URL('/mcp', window.location.href).href;
document.getElementById('endpoint').textContent = endpoint;
document.getElementById('copy').addEventListener('click', async () => {{
  await navigator.clipboard.writeText(endpoint);
  document.getElementById('copy').textContent = 'Copied';
}});
</script>
"""
    return _page(cfg.server_name, body)


def not_found_page() -> str:
    return _page(
        "Page not found · MkDocs MCP",
        '<div class="eyebrow">404 · Page not found</div>'
        "<h1>Nothing here.</h1><p>The page you requested does not exist on this server.</p>"
        '<a class="button" href="/">Go to home</a>',
    )
