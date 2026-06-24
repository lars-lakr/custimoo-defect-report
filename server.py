"""Minimal HTTP server that triggers GitHub Actions workflow and shows status."""
import http.server, json, os, urllib.request, threading, time

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = "lars-lakr/custimoo-defect-report"
WORKFLOW_FILE = "deploy.yml"

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/refresh":
            self._trigger()
        elif self.path == "/api/status":
            self._status()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        self.do_GET()

    def _trigger(self):
        if self.path == "/api/refresh":
            # Check if already processing
            if self._already_running():
                self._json(429, {"ok": False, "error": "Workflow already running — please wait"})
                return
            try:
                url = f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches"
                data = json.dumps({"ref": "main"}).encode()
                req = urllib.request.Request(url, data=data, method="POST",
                    headers={"Authorization": f"Bearer {GITHUB_TOKEN}",
                             "Accept": "application/vnd.github+json",
                             "Content-Type": "application/json"})
                with urllib.request.urlopen(req) as resp:
                    self._json(200, {"ok": True, "message": "Refresh triggered — report updates in ~2 min"})
            except Exception as e:
                msg = str(e)
                if "403" in msg:
                    msg = "GitHub token missing or expired — contact admin"
                self._json(500, {"ok": False, "error": msg})

    def _status(self):
        try:
            url = f"https://api.github.com/repos/{REPO}/actions/runs?per_page=1&event=push&status=completed"
            req = urllib.request.Request(url,
                headers={"Authorization": f"Bearer {GITHUB_TOKEN}",
                         "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read())
            runs = data.get("workflow_runs", [])
            if runs:
                run = runs[0]
                self._json(200, {
                    "conclusion": run["conclusion"],
                    "updated_at": run["updated_at"],
                    "html_url": run["html_url"]
                })
            else:
                self._json(200, {"conclusion": "unknown"})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _already_running(self):
        try:
            url = f"https://api.github.com/repos/{REPO}/actions/runs?per_page=1&status=in_progress"
            req = urllib.request.Request(url,
                headers={"Authorization": f"Bearer {GITHUB_TOKEN}",
                         "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read())
            return len(data.get("workflow_runs", [])) > 0
        except:
            return False

    def _json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass  # quiet

if __name__ == "__main__":
    port = int(os.environ.get("API_PORT", 8080))
    httpd = http.server.HTTPServer(("0.0.0.0", port), Handler)
    print(f"API server on port {port}")
    httpd.serve_forever()
