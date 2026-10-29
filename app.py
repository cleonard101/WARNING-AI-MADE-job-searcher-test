"""Teen Job Compass local app. Python 3.10+, standard library only.

Run ``python app.py``, then open http://127.0.0.1:8000.
This development server deliberately binds to your own computer only.
"""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import secrets
import threading
import time
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent
MAX_BODY = 24_000


class ProfileError(ValueError):
    def __init__(self, message: str, fields: list[str] | None = None):
        super().__init__(message)
        self.fields = fields or []


def validate_profile(data: object) -> dict:
    """Normalize form values without inferring any missing preferences."""
    if not isinstance(data, dict):
        raise ProfileError("Send a JSON object with age, interests, and location.")
    allowed = {
        "age", "interests", "location", "max_distance_miles",
        "max_commute_minutes", "transportation", "work_arrangement",
        "availability", "max_hours_per_week", "employment_type", "skills",
        "minimum_hourly_pay", "must_haves",
    }
    if set(data) - allowed:
        raise ProfileError("The search contains an unsupported field.")
    missing = [name for name in ("age", "interests", "location")
               if data.get(name) is None or data.get(name) == ""
               or (isinstance(data.get(name), str) and not data[name].strip())]
    if missing:
        raise ProfileError("Please add your " + ", ".join(missing) + ".", missing)

    def number(name: str, low: float, high: float, *, integer=False):
        value = data.get(name)
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            raise ProfileError(f"{name.replace('_', ' ').capitalize()} must be a number.", [name])
        try:
            value = float(value)
        except (ValueError, OverflowError):
            raise ProfileError(f"{name.replace('_', ' ').capitalize()} must be a number.", [name])
        if not math.isfinite(value) or not low <= value <= high or (integer and not value.is_integer()):
            raise ProfileError(f"{name.replace('_', ' ').capitalize()} must be between {low:g} and {high:g}." , [name])
        return int(value) if integer else value

    def text(name: str, limit: int):
        value = data.get(name, "")
        if value is None:
            return ""
        if not isinstance(value, str):
            raise ProfileError(f"{name.replace('_', ' ').capitalize()} must be text.", [name])
        value = value.strip()
        if len(value) > limit:
            raise ProfileError(f"Keep {name.replace('_', ' ')} under {limit} characters.", [name])
        if any(ord(c) < 32 and c not in "\n\r\t" for c in value):
            raise ProfileError("Please remove control characters from the form.", [name])
        return value

    result = {
        "age": number("age", 14, 18, integer=True),
        "interests": text("interests", 600),
        "location": text("location", 160),
        "max_distance_miles": number("max_distance_miles", 0, 500),
        "max_commute_minutes": number("max_commute_minutes", 0, 240),
        "transportation": text("transportation", 300),
        "availability": text("availability", 600),
        "max_hours_per_week": number("max_hours_per_week", 0, 168),
        "skills": text("skills", 1200),
        "minimum_hourly_pay": number("minimum_hourly_pay", 0, 1000),
        "must_haves": text("must_haves", 800),
    }
    choices = {
        "work_arrangement": {"any", "in_person", "remote", "hybrid"},
        "employment_type": {"any", "part_time", "seasonal", "temporary", "internship", "apprenticeship"},
    }
    for name, options in choices.items():
        value = data.get(name) or "any"
        if not isinstance(value, str) or value not in options:
            raise ProfileError(f"Choose a supported {name.replace('_', ' ')}.", [name])
        result[name] = value
    return result


def offline_plan(profile: dict) -> dict:
    """Useful non-AI fallback; never manufacture a vacancy or eligibility claim."""
    location = " ".join(profile["location"].split())
    interests = " ".join(profile["interests"].split())[:180]
    kind = profile["employment_type"].replace("_", " ")
    kind = "paid" if kind == "any" else kind
    age = profile["age"]
    unspecified = []
    for field, label in [("availability", "Availability"), ("transportation", "Transportation"),
                         ("skills", "Experience"), ("minimum_hourly_pay", "Minimum pay")]:
        if profile.get(field) in (None, ""):
            unspecified.append(f"{label} is unspecified; no preference was assumed.")
    return {
        "mode": "offline",
        "search_date": datetime.now().astimezone().date().isoformat(),
        "summary": f"Search plan for a {age}-year-old interested in {interests}, near {location}. No live search or AI call was performed.",
        "assumptions": unspecified,
        "best_matches": [], "needs_confirmation": [], "leads": [],
        "next_steps": [
            "Use these search phrases to find employer career pages and local workforce resources.",
            f"Open each specific listing and check whether that position hires applicants age {age}; also check current official youth-work rules.",
            "Compare duties, actual worksite, pay, hours, and your travel limits before applying on the employer's site.",
        ],
        "search_phrases": [
            f"{interests} {kind} jobs {location}",
            f'jobs "minimum age" "{age}" {location}',
            f'"paid" "youth" employment {location}',
            f'{interests} "no experience" jobs {location}',
            f'{kind} "careers" "hiring" {location}',
        ],
        "limitations": [
            "Live search needs an OpenAI API key in the server's .env file. This plan is generated from your form by ordinary code.",
            "No current openings, pay, age eligibility, travel distances, or schedules have been verified.",
            "For any strict commute limit, obtain route information; a city or ZIP code cannot establish a trip from your home.",
        ],
        "work_rules": [], "sources": [], "excluded_count": 0,
    }


def read_env(path: Path) -> dict[str, str]:
    """Read a tiny .env format. Never evaluate shell syntax or interpolate values."""
    values = {}
    allowed = {"OPENAI_API_KEY", "OPENAI_MODEL", "PORT", "API_TIMEOUT_SECONDS"}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if key not in allowed:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


@dataclass(frozen=True)
class Config:
    api_key: str = ""
    model: str = "gpt-5.6-terra"
    port: int = 8000
    timeout: int = 180


def load_config(*, force_offline=False) -> Config:
    values = read_env(ROOT / ".env")
    for key in ("OPENAI_API_KEY", "OPENAI_MODEL", "PORT", "API_TIMEOUT_SECONDS"):
        if key in os.environ:
            values[key] = os.environ[key]
    try:
        port = int(values.get("PORT", "8000"))
        timeout = int(values.get("API_TIMEOUT_SECONDS", "180"))
        if not 1 <= port <= 65535 or not 30 <= timeout <= 600:
            raise ValueError
    except ValueError:
        raise SystemExit("PORT must be 1-65535 and API_TIMEOUT_SECONDS must be 30-600.")
    return Config(
        api_key="" if force_offline else values.get("OPENAI_API_KEY", "").strip(),
        model=values.get("OPENAI_MODEL", "gpt-5.6-terra").strip() or "gpt-5.6-terra",
        port=port, timeout=timeout,
    )


class AppState:
    def __init__(self, config: Config, engine_factory=None):
        self.config = config
        self.csrf_token = secrets.token_urlsafe(32)
        self.search_lock = threading.Lock()
        self.rate_lock = threading.Lock()
        self.recent_calls: deque[float] = deque()
        self.engine_factory = engine_factory

    def allow_live_call(self) -> bool:
        with self.rate_lock:
            now = time.monotonic()
            while self.recent_calls and self.recent_calls[0] <= now - 60:
                self.recent_calls.popleft()
            if len(self.recent_calls) >= 3:
                return False
            self.recent_calls.append(now)
            return True


def make_server(config: Config | None = None, *, port: int | None = None, engine_factory=None):
    config = config or load_config()
    state = AppState(config, engine_factory)

    class Handler(BaseHTTPRequestHandler):
        server_version = "TeenJobCompass"

        def log_message(self, *_):
            # Profiles, URLs, API keys, and searches are not written to logs.
            pass

        def allowed_hosts(self) -> set[str]:
            actual_port = self.server.server_address[1]
            return {f"127.0.0.1:{actual_port}", f"localhost:{actual_port}"}

        def safe_host(self) -> bool:
            return self.headers.get("Host", "").lower() in self.allowed_hosts()

        def finish_headers(self, content_type: str, length: int):
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
            self.end_headers()

        def json_response(self, status: int, data: dict):
            body = json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.finish_headers("application/json; charset=utf-8", len(body))
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            if not self.safe_host():
                self.json_response(403, {"error": "Open the app using its localhost address."})
                return
            path = urlsplit(self.path).path
            if path == "/api/config":
                self.json_response(200, {"live_available": bool(state.config.api_key),
                                         "model": state.config.model, "csrf_token": state.csrf_token})
                return
            if path == "/api/demo":
                from demo import demo_results
                self.json_response(200, demo_results())
                return
            if path == "/api/health":
                self.json_response(200, {"status": "ok"})
                return
            static = {
                "/": ("index.html", "text/html; charset=utf-8"),
                "/index.html": ("index.html", "text/html; charset=utf-8"),
                "/styles.css": ("styles.css", "text/css; charset=utf-8"),
                "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            }
            if path not in static:
                self.json_response(404, {"error": "Page not found."})
                return
            filename, content_type = static[path]
            try:
                body = (ROOT / "static" / filename).read_bytes()
            except OSError:
                self.json_response(503, {"error": "The app files are incomplete. Extract the whole project folder first."})
                return
            self.send_response(200)
            self.finish_headers(content_type, len(body))
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_POST(self):
            if not self.safe_host():
                self.json_response(403, {"error": "Open the app using its localhost address."})
                return
            origin = self.headers.get("Origin")
            allowed_origins = {"http://" + host for host in self.allowed_hosts()}
            if origin and origin not in allowed_origins:
                self.json_response(403, {"error": "This request must come from the local app."})
                return
            if self.headers.get("Sec-Fetch-Site") == "cross-site":
                self.json_response(403, {"error": "This request must come from the local app."})
                return
            provided_token = self.headers.get("X-CSRF-Token", "")
            if not provided_token.isascii() or not secrets.compare_digest(provided_token, state.csrf_token):
                self.json_response(403, {"error": "Refresh the app and try again."})
                return
            if urlsplit(self.path).path != "/api/search":
                self.json_response(404, {"error": "Endpoint not found."})
                return
            if self.headers.get_content_type() != "application/json":
                self.json_response(415, {"error": "Send the search as application/json."})
                return
            if self.headers.get("Transfer-Encoding"):
                self.json_response(400, {"error": "This local app requires Content-Length."})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if not 1 <= length <= MAX_BODY:
                self.json_response(413, {"error": "The search form is empty or too large."})
                return
            self.connection.settimeout(15)
            try:
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError
                def invalid_constant(_):
                    raise ValueError("Non-finite JSON value")
                payload = json.loads(raw.decode("utf-8"), parse_constant=invalid_constant)
                profile = validate_profile(payload)
            except ProfileError as exc:
                self.json_response(422, {"error": str(exc), "fields": exc.fields})
                return
            except (ValueError, UnicodeDecodeError, TimeoutError, RecursionError):
                self.json_response(400, {"error": "The search form could not be read. Please try again."})
                return
            if not state.config.api_key:
                self.json_response(200, offline_plan(profile))
                return
            if not state.search_lock.acquire(blocking=False):
                self.json_response(409, {"error": "A search is already running. Wait for it to finish before starting another."})
                return
            try:
                if not state.allow_live_call():
                    self.json_response(429, {"error": "Please wait a minute before starting another live search."})
                    return
                try:
                    from engine import JobSearchEngine, EngineError
                except ImportError:
                    self.json_response(503, {"error": "The AI engine is missing. Extract the entire project folder and restart the app."})
                    return
                factory = state.engine_factory or JobSearchEngine
                try:
                    engine = factory(state.config.api_key, model=state.config.model, timeout=state.config.timeout)
                    result = engine.search(profile)
                    self.json_response(200, result)
                except EngineError as exc:
                    self.json_response(exc.status, {"error": str(exc)})
                except Exception:
                    # Never echo raw provider messages, prompts, keys, or tracebacks.
                    self.json_response(502, {"error": "The search could not be completed. No results were treated as verified. Try again later or use example results."})
            finally:
                state.search_lock.release()

    server = ThreadingHTTPServer(("127.0.0.1", config.port if port is None else port), Handler)
    server.daemon_threads = True
    server.app_state = state
    return server


def main():
    parser = argparse.ArgumentParser(description="Run Teen Job Compass on your own computer.")
    parser.add_argument("--port", type=int, help="Local port, default 8000.")
    parser.add_argument("--offline", action="store_true", help="Disable all AI requests, even if a key is configured.")
    args = parser.parse_args()
    if args.port is not None and not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    config = load_config(force_offline=args.offline)
    try:
        server = make_server(config, port=args.port)
    except OSError:
        raise SystemExit("Could not open the local port. Try: python app.py --port 8001")
    mode = "Live AI search is configured" if config.api_key else "Search-plan mode; no API key configured"
    print(f"Teen Job Compass\nOpen http://127.0.0.1:{server.server_address[1]}\n{mode}\nPress Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
