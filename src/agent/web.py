from __future__ import annotations

import html
import json
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from .app import Session, SupportAgent


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


class WebState:
    agent = SupportAgent()
    session = Session()
    last_response = None


def page(answer_html: str = "", question: str = "", debug: bool = False) -> bytes:
    checked = "checked" if debug else ""
    body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Aster & Row Support Agent</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #1f2933;
      --muted: #5f6b7a;
      --line: #d8dee6;
      --panel: #ffffff;
      --bg: #f4f6f8;
      --accent: #146c5c;
      --accent-dark: #0d4f43;
      --warn: #945c00;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
    }}
    header {{
      padding: 28px 32px 18px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}
    main {{
      max-width: 960px;
      margin: 0 auto;
      padding: 28px 20px 48px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
      line-height: 1.15;
      letter-spacing: 0;
    }}
    p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.5;
    }}
    form {{
      display: grid;
      gap: 14px;
      padding: 20px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    label {{
      font-weight: 650;
      font-size: 14px;
    }}
    textarea {{
      width: 100%;
      min-height: 112px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
      font: inherit;
      line-height: 1.45;
    }}
    .row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }}
    .check {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: 14px;
      font-weight: 500;
    }}
    button {{
      appearance: none;
      border: 0;
      background: var(--accent);
      color: white;
      border-radius: 6px;
      padding: 10px 16px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }}
    button:hover {{ background: var(--accent-dark); }}
    .examples {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 10px;
      margin: 18px 0;
    }}
    .example {{
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fbfcfd;
      color: var(--muted);
      font-size: 14px;
    }}
    .answer {{
      margin-top: 18px;
      padding: 20px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .answer h2 {{
      margin: 0 0 10px;
      font-size: 18px;
    }}
    .answer-text {{
      white-space: pre-wrap;
      line-height: 1.55;
    }}
    .sources {{
      margin-top: 14px;
      padding-top: 14px;
      border-top: 1px solid var(--line);
    }}
    .sources ul {{
      margin: 8px 0 0;
      padding-left: 20px;
    }}
    .handoff {{
      margin-top: 14px;
      color: var(--warn);
      font-weight: 700;
    }}
    pre {{
      overflow: auto;
      padding: 12px;
      border-radius: 6px;
      background: #111827;
      color: #e5e7eb;
      font-size: 13px;
      line-height: 1.45;
    }}
  </style>
</head>
<body>
  <header>
    <h1>Aster & Row Support Agent</h1>
    <p>Ask about returns, shipping, warranty, product care, or customer-safe order status.</p>
  </header>
  <main>
    <form method="post">
      <label for="question">Customer question</label>
      <textarea id="question" name="question" placeholder="Where is ORD-1007?">{html.escape(question)}</textarea>
      <div class="row">
        <label class="check"><input type="checkbox" name="debug" value="1" {checked}> Show debug trace</label>
        <button type="submit">Ask Agent</button>
      </div>
    </form>
    <div class="examples">
      <div class="example">How long do I have to return an unused backpack?</div>
      <div class="example">Where is ORD-1007 and when should it arrive?</div>
      <div class="example">Do you ship internationally? What about Canada?</div>
      <div class="example">Can I put the entire Breeze Tumbler in the dishwasher?</div>
    </div>
    {answer_html}
  </main>
</body>
</html>"""
    return body.encode("utf-8")


def render_answer(question: str, debug: bool) -> str:
    response = WebState.agent.respond(question, session=WebState.session, debug=debug)
    source_html = ""
    if response.sources:
        items = "".join(f"<li>{html.escape(source)}</li>" for source in response.sources)
        source_html = f'<div class="sources"><strong>Sources</strong><ul>{items}</ul></div>'
    handoff_html = '<div class="handoff">Human handoff recommended: yes</div>' if response.handoff else ""
    trace_html = ""
    if debug:
        trace = html.escape(json.dumps(response.trace, indent=2, sort_keys=True))
        trace_html = f"<h2>Debug Trace</h2><pre>{trace}</pre>"
    return f"""
    <section class="answer">
      <h2>Answer</h2>
      <div class="answer-text">{html.escape(response.answer)}</div>
      {source_html}
      {handoff_html}
      {trace_html}
    </section>
    """


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self._send(page())

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        form = parse_qs(raw)
        question = form.get("question", [""])[0].strip()
        debug = form.get("debug", ["0"])[0] == "1"
        answer = render_answer(question, debug) if question else ""
        self._send(page(answer, question, debug))

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send(self, content: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Aster & Row web form")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Aster & Row web form running at http://{args.host}:{args.port}", flush=True)
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
