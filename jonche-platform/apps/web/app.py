"""
apps/web/app.py
Jonche Platform — Web frontend (Flask)
Serves the dashboard and proxies API calls.
"""

import os
from functools import wraps

import requests
from flask import Flask, render_template, jsonify, request, redirect, url_for, make_response
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

COOKIE_NAME = "jonche_token"
RETAILER_COOKIE_NAME = "jonche_retailer_token"


def _api_base() -> str:
    """Absolute API base URL for server-side requests."""
    env = os.getenv("API_BASE_URL")
    if env:
        return env.rstrip("/")
    if request.host.startswith("localhost"):
        return "http://localhost:5001/api"
    return request.url_root.rstrip("/") + "/api"


def require_admin_web(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if app.config.get("TESTING"):
            return f(*args, **kwargs)
        if not request.cookies.get(COOKIE_NAME):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated


def require_retailer_web(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if app.config.get("TESTING"):
            return f(*args, **kwargs)
        if not request.cookies.get(RETAILER_COOKIE_NAME):
            return redirect(url_for("retailer_login", next=request.path))
        return f(*args, **kwargs)
    return decorated


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
@require_admin_web
def dashboard():
    """Main command center dashboard."""
    return render_template("dashboard.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", next=request.args.get("next"))

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    next_path = request.form.get("next") or "/"

    if not email or not password:
        return render_template("login.html", error="Email and password required", next=next_path), 400

    try:
        res = requests.post(
            f"{_api_base()}/auth/admin/login",
            json={"email": email, "password": password},
            timeout=8,
        )
    except requests.RequestException:
        return render_template("login.html", error="API unavailable", next=next_path), 502

    if res.status_code != 200:
        return render_template("login.html", error="Invalid credentials", next=next_path), 401

    token = (res.json() or {}).get("token")
    if not token:
        return render_template("login.html", error="Login failed", next=next_path), 502

    resp = make_response(redirect(next_path))
    resp.set_cookie(COOKIE_NAME, token, httponly=True, samesite="Lax")
    return resp


@app.route("/logout", methods=["POST", "GET"])
def logout():
    resp = make_response(redirect(url_for("login")))
    resp.delete_cookie(COOKIE_NAME)
    return resp


@app.route("/drops")
@require_admin_web
def drops():
    """Live drops page."""
    return render_template("drops.html")


@app.route("/retailers")
@require_admin_web
def retailers():
    """Retailer portal page."""
    return render_template("retailers.html")


@app.route("/vip")
@require_admin_web
def vip():
    """VIP club page."""
    return render_template("vip.html")


@app.route("/analytics")
@require_admin_web
def analytics():
    """Analytics page."""
    return render_template("analytics.html")


@app.route("/certificates")
@require_admin_web
def certificates():
    """Authenticity certificates page."""
    return render_template("certificates.html")


@app.route("/admin")
@require_admin_web
def admin_controls():
    """Admin utilities: exports + overrides + allocation adjustments."""
    return render_template("admin.html")


@app.route("/verify/<token>")
def verify(token: str):
    """Public branded certificate verification page (no login)."""
    data = None
    error = None
    try:
        res = requests.get(f"{_api_base()}/certificates/verify/{token}", timeout=8)
        if res.status_code == 200:
            data = res.json()
        else:
            if res.headers.get("content-type", "").startswith("application/json"):
                error = (res.json() or {}).get("error") or "Not found"
            else:
                error = "Not found"
    except requests.RequestException:
        error = "Verification service unavailable"
    return render_template("verify.html", token=token, data=data, error=error)


@app.route("/preorder", methods=["GET", "POST"])
def preorder():
    """Public pre-order intent capture form."""
    if request.method == "GET":
        drops = []
        try:
            res = requests.get(f"{_api_base()}/drops/", timeout=8)
            if res.status_code == 200:
                drops = res.json() or []
        except requests.RequestException:
            drops = []
        return render_template("preorder.html", drops=drops)

    payload = {
        "drop_id": request.form.get("drop_id"),
        "email": (request.form.get("email") or "").strip().lower(),
        "name": (request.form.get("name") or "").strip(),
        "size": (request.form.get("size") or "").strip(),
        "deposit_cents": int(request.form.get("deposit_cents") or 0),
    }
    required = ["drop_id", "email", "name", "size"]
    if any(not payload[k] for k in required):
        return render_template("preorder.html", error="All fields required", drops=[]), 400

    try:
        res = requests.post(f"{_api_base()}/preorders/", json=payload, timeout=8)
    except requests.RequestException:
        return render_template("preorder.html", error="API unavailable", drops=[]), 502

    if res.status_code not in (200, 201):
        msg = "Already captured for this drop" if res.status_code == 409 else "Could not submit"
        return render_template("preorder.html", error=msg, drops=[]), res.status_code

    return render_template("preorder_success.html", preorder=res.json())


# ── Retailer Portal (separate login) ───────────────────────────────────────────

@app.route("/retailer/login", methods=["GET", "POST"])
def retailer_login():
    if request.method == "GET":
        return render_template("retailer_login.html", next=request.args.get("next"))

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    next_path = request.form.get("next") or "/retailer"

    if not email or not password:
        return render_template("retailer_login.html", error="Email and password required", next=next_path), 400

    try:
        res = requests.post(
            f"{_api_base()}/auth/retailer/login",
            json={"email": email, "password": password},
            timeout=8,
        )
    except requests.RequestException:
        return render_template("retailer_login.html", error="API unavailable", next=next_path), 502

    if res.status_code != 200:
        return render_template("retailer_login.html", error="Invalid credentials", next=next_path), 401

    token = (res.json() or {}).get("token")
    if not token:
        return render_template("retailer_login.html", error="Login failed", next=next_path), 502

    resp = make_response(redirect(next_path))
    resp.set_cookie(RETAILER_COOKIE_NAME, token, httponly=True, samesite="Lax")
    return resp


@app.route("/retailer/logout", methods=["POST", "GET"])
def retailer_logout():
    resp = make_response(redirect(url_for("retailer_login")))
    resp.delete_cookie(RETAILER_COOKIE_NAME)
    return resp


@app.route("/retailer")
@require_retailer_web
def retailer_portal():
    return render_template("retailer_portal.html")


@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "app": "jonche-web"})


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("WEB_PORT", 5000))
    debug = os.getenv("FLASK_ENV", "development") == "development"
    print(f"🖤 Jonche Web running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
