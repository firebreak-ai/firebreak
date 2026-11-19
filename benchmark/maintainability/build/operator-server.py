"""A simulated operator for one build: operator-server.py <port> <spec-file> <brief-file> <log-file>
Reads the full specification and the brief once, at start, and keeps them in memory, so the answers can be locked
afterwards. POST / with a question as the body returns the operator's answer as plain text. Each question goes to one
fresh headless session with no tools, in an empty folder. Every question and answer is appended to <log-file> as a
JSON line with the session's cost. Listens on 127.0.0.1 only."""
import http.server, json, os, subprocess, sys, tempfile, time

port, spec, brief, log = int(sys.argv[1]), open(sys.argv[2]).read(), open(sys.argv[3]).read(), sys.argv[4]
DROP = ("CLAUDE_CODE_CHILD_SESSION", "CLAUDE_CODE_SESSION_ID", "CLAUDECODE", "CLAUDE_CODE_BRIDGE_SESSION_ID",
        "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_MESSAGING_TOKEN", "CLAUDE_CODE_SESSION_ATTENDED")
ENV = {k: v for k, v in os.environ.items() if k not in DROP}


def answer(question):
    prompt = brief.replace("SPEC", spec).replace("QUESTION", question)
    with tempfile.TemporaryDirectory() as d:
        p = subprocess.run(["claude", "--print", "--model", "claude-opus-5-5", "--tools", "", "--strict-mcp-config",
                            "--setting-sources", "project,local", "--output-format", "json"],
                           input=prompt, capture_output=True, text=True, cwd=d, env=ENV, timeout=600, check=False)
    try:
        r = json.loads(p.stdout)
        return r.get("result") or "", r.get("total_cost_usd")
    except ValueError:
        return "", None


class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        q = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode("utf-8", "replace").strip()
        try:
            a, cost = answer(q) if q else ("", None)
        except subprocess.TimeoutExpired:
            a, cost = "", None
        with open(log, "a") as f:
            f.write(json.dumps({"time": time.strftime("%FT%TZ", time.gmtime()), "question": q, "answer": a, "cost": cost}) + "\n")
        body = (a or "The operator did not answer. Ask again in a moment.").encode()
        self.send_response(200); self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def log_message(self, *a):
        pass


http.server.ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
