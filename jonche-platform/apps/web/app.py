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

ADMIN_COOKIE_NAME = "jonche_admin_token"
LEGACY_ADMIN_COOKIE_NAME = "jonche_token"
MEMBER_COOKIE_NAME = "jonche_member_token"
RETAILER_COOKIE_NAME = "jonche_retailer_token"


def _api_base() -> str:
    """Absolute API base URL for server-side requests."""
    env = os.getenv("API_BASE_URL")
    if env:
        return env.rstrip("/")
    if request.host.startswith(("localhost", "127.0.0.1", "[::1]")):
        return "http://localhost:5001/api"
    return request.url_root.rstrip("/") + "/api"


def require_admin_web(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if app.config.get("TESTING"):
            return f(*args, **kwargs)
        if not (request.cookies.get(ADMIN_COOKIE_NAME) or request.cookies.get(LEGACY_ADMIN_COOKIE_NAME)):
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
def dashboard():
    """
    Default landing:
    - Admins with a valid cookie land on the command center dashboard.
    - Everyone else sees the storefront first.
    """
    if request.cookies.get(ADMIN_COOKIE_NAME) or request.cookies.get(LEGACY_ADMIN_COOKIE_NAME):
        return render_template("dashboard.html")
    return redirect(url_for("store_homepage"))


@app.route("/dashboard")
@require_admin_web
def dashboard_admin():
    """Admin command center dashboard."""
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
    resp.set_cookie(ADMIN_COOKIE_NAME, token, httponly=True, samesite="Lax")
    resp.delete_cookie(LEGACY_ADMIN_COOKIE_NAME)
    return resp


@app.route("/logout", methods=["POST", "GET"])
def logout():
    resp = make_response(redirect(url_for("login")))
    resp.delete_cookie(ADMIN_COOKIE_NAME)
    resp.delete_cookie(LEGACY_ADMIN_COOKIE_NAME)
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


@app.route("/admin/partners")
@require_admin_web
def admin_partners():
    """Admin view: recent partner applications."""
    token = request.cookies.get(ADMIN_COOKIE_NAME) or request.cookies.get(LEGACY_ADMIN_COOKIE_NAME)
    applications = []
    error = None
    try:
        res = requests.get(
            f"{_api_base()}/partners/applications",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8,
        )
        if res.status_code == 200:
            applications = res.json() or []
        else:
            if res.headers.get("content-type", "").startswith("application/json"):
                error = (res.json() or {}).get("error") or "Could not load applications"
            else:
                error = "Could not load applications"
    except requests.RequestException:
        error = "API unavailable"
    return render_template("partners_admin.html", applications=applications, error=error)


@app.route("/admin/dashboards")
@require_admin_web
def admin_dashboards():
    """Admin dashboard: partner management, earnings, commissions, announcements."""
    return render_template("admin_partners.html")


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


# ── Partners / Programs (Public Intake) ───────────────────────────────────────

PARTNER_PROGRAMS = {
    "retail_alliance": {
        "route": "/retail-alliance",
        "title": "Jonche Retail Alliance",
        "subtitle": "Exclusive sneaker allocations + retail growth support.",
        "cta": "Offer exclusive sneakers and grow your store revenue.",
        "commission": "Program-based commissions and allocations (case-by-case).",
        "benefits": [
            "Exclusive sneaker allocations",
            "Co-branded opportunities",
            "Marketing support",
            "Funding access (if qualified)",
            "POS system options",
            "Early product releases",
        ],
    },
    "affiliate_creators": {
        "route": "/affiliates",
        "title": "Jonche Affiliate Creators",
        "subtitle": "Earn while you create — promote exclusive releases.",
        "cta": "Earn 10–15% promoting exclusive Jonche releases.",
        "commission": "10–15% per sale.",
        "benefits": [
            "10–15% per sale",
            "Unique referral link",
            "Early access to drops",
            "Creator spotlight opportunities",
            "Performance bonuses",
        ],
    },
    "referral_network": {
        "route": "/referral-network",
        "title": "Jonche Strategic Referral Network",
        "subtitle": "High-ticket introductions with high commissions.",
        "cta": "Earn high commissions connecting businesses and buyers.",
        "commission": "20% bulk order commission + 25% of earned funding commission.",
        "benefits": [
            "20% bulk order commissions",
            "25% funding referral commissions",
            "Priority payouts",
            "Partner recognition",
            "High-ticket deal opportunities",
        ],
    },
    "executives": {
        "route": "/executives",
        "title": "Jonche Executives",
        "subtitle": "Premium deal flow and strategic collaboration.",
        "cta": "Partner with Jonche on premium deals and strategic growth.",
        "commission": "Premium eligibility (case-by-case).",
        "benefits": [
            "Premium deal flow",
            "Larger commission eligibility",
            "Co-brand opportunities",
            "Territory partnerships",
            "Direct collaboration with Jonche leadership",
        ],
    },
}


def _submit_partner_application(program_type: str):
    utm = {
        "utm_source": request.args.get("utm_source"),
        "utm_medium": request.args.get("utm_medium"),
        "utm_campaign": request.args.get("utm_campaign"),
        "utm_content": request.args.get("utm_content"),
        "utm_term": request.args.get("utm_term"),
    }
    utm = {k: v for k, v in utm.items() if v}
    payload = {
        "program_type": program_type,
        "source": (request.form.get("source") or request.args.get("src") or "").strip() or None,
        "utm": utm,
        "full_name": (request.form.get("full_name") or "").strip(),
        "business_name": (request.form.get("business_name") or "").strip() or None,
        "email": (request.form.get("email") or "").strip().lower(),
        "phone": (request.form.get("phone") or "").strip() or None,
        "website_or_social": (request.form.get("website_or_social") or "").strip() or None,
        "city": (request.form.get("city") or "").strip() or None,
        "state": (request.form.get("state") or "").strip() or None,
        "estimated_monthly_reach": (request.form.get("estimated_monthly_reach") or "").strip() or None,
        "network_type": (request.form.get("network_type") or "").strip() or None,
        "interested_in": request.form.getlist("interested_in"),
        "additional_notes": (request.form.get("additional_notes") or "").strip() or None,
    }
    if not payload["full_name"] or not payload["email"]:
        return None, "Full name and email are required."
    try:
        res = requests.post(f"{_api_base()}/partners/apply", json=payload, timeout=8)
    except requests.RequestException:
        return None, "Service unavailable. Please try again."
    if res.status_code not in (200, 201):
        err = "Could not submit. Please try again."
        if res.headers.get("content-type", "").startswith("application/json"):
            err = (res.json() or {}).get("error") or err
        return None, err
    return res.json(), None


@app.route("/partners")
def partners_overview():
    """Public overview page with program links."""
    return render_template("partners.html", programs=PARTNER_PROGRAMS)


@app.route("/affiliates", methods=["GET", "POST"])
def partners_affiliates():
    program = PARTNER_PROGRAMS["affiliate_creators"]
    if request.method == "POST":
        _, error = _submit_partner_application("affiliate_creators")
        if error:
            return render_template("affiliates.html", program=program, error=error), 400
        return redirect(url_for("thank_you", program="affiliate_creators"))
    return render_template("affiliates.html", program=program)


@app.route("/retail-alliance", methods=["GET", "POST"])
def partners_retail_alliance():
    program = PARTNER_PROGRAMS["retail_alliance"]
    if request.method == "POST":
        _, error = _submit_partner_application("retail_alliance")
        if error:
            return render_template("retail_alliance.html", program=program, error=error), 400
        return redirect(url_for("thank_you", program="retail_alliance"))
    return render_template("retail_alliance.html", program=program)


@app.route("/referral-network", methods=["GET", "POST"])
def partners_referral_network():
    program = PARTNER_PROGRAMS["referral_network"]
    if request.method == "POST":
        _, error = _submit_partner_application("referral_network")
        if error:
            return render_template("referral_network.html", program=program, error=error), 400
        return redirect(url_for("thank_you", program="referral_network"))
    return render_template("referral_network.html", program=program)


@app.route("/executives", methods=["GET", "POST"])
def partners_executives():
    program = PARTNER_PROGRAMS["executives"]
    if request.method == "POST":
        _, error = _submit_partner_application("executives")
        if error:
            return render_template("executives.html", program=program, error=error), 400
        return redirect(url_for("thank_you", program="executives"))
    return render_template("executives.html", program=program)


@app.route("/thank-you")
def thank_you():
    """Public generic confirmation page for form submissions."""
    program_type = request.args.get("program")
    program = PARTNER_PROGRAMS.get(program_type) if program_type else None
    return render_template("thank_you.html", program=program)


# ── Store / Products ───────────────────────────────────────────────────────

@app.route("/store")
def store_homepage():
    """Store landing page with commercials carousel and featured products."""
    commercials = []
    categories = []
    featured_products = []
    
    try:
        # Get commercials for carousel
        res = requests.get(f"{_api_base()}/products/commercials", timeout=8)
        if res.status_code == 200:
            commercials = res.json() or []
    except requests.RequestException:
        pass

    try:
        # Get categories
        res = requests.get(f"{_api_base()}/products/categories", timeout=8)
        if res.status_code == 200:
            categories = res.json() or []
    except requests.RequestException:
        pass

    try:
        # Get featured products
        res = requests.get(f"{_api_base()}/products/?per_page=8", timeout=8)
        if res.status_code == 200:
            data = res.json() or {}
            featured_products = data.get("items", [])
    except requests.RequestException:
        pass

    return render_template(
        "store.html",
        commercials=commercials,
        categories=categories,
        featured_products=featured_products,
    )


@app.route("/store/products")
def store_products():
    """Browse all store products with filtering."""
    return render_template("products.html")


@app.route("/store/product/<int:product_id>")
def store_product_detail(product_id):
    """Product detail page."""
    product = None
    error = None
    
    try:
        res = requests.get(f"{_api_base()}/products/{product_id}", timeout=8)
        if res.status_code == 200:
            product = res.json()
        else:
            error = "Product not found"
    except requests.RequestException:
        error = "Could not load product"

    return render_template("product_detail.html", product=product, error=error)


@app.route("/store/cart")
def store_cart():
    """Shopping cart page."""
    return render_template("cart.html")


@app.route("/store/checkout")
def store_checkout():
    """Checkout page (requires login)."""
    token = request.cookies.get(MEMBER_COOKIE_NAME)
    if not token:
        return redirect(url_for("account_login", next="/store/checkout"))
    return render_template("checkout.html")


@app.route("/admin/store")
@require_admin_web
def admin_store():
    """Store admin management page."""
    return render_template("admin_store.html")



# ── Retailer Portal (separate login) ───────────────────────────────────────────

# ── Member Accounts (Store) ────────────────────────────────────────────────────

@app.route("/account/login", methods=["GET", "POST"])
def account_login():
    if request.method == "GET":
        return render_template("member_login.html", next=request.args.get("next"))

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    next_path = request.form.get("next") or "/store"

    if not email or not password:
        return render_template("member_login.html", error="Email and password required", next=next_path), 400

    try:
        res = requests.post(
            f"{_api_base()}/auth/member/login",
            json={"email": email, "password": password},
            timeout=8,
        )
    except requests.RequestException:
        return render_template("member_login.html", error="API unavailable", next=next_path), 502

    if res.status_code != 200:
        return render_template("member_login.html", error="Invalid credentials", next=next_path), 401

    token = (res.json() or {}).get("token")
    if not token:
        return render_template("member_login.html", error="Login failed", next=next_path), 502

    resp = make_response(redirect(next_path))
    resp.set_cookie(MEMBER_COOKIE_NAME, token, httponly=True, samesite="Lax")
    return resp


@app.route("/account/register", methods=["GET", "POST"])
def account_register():
    if request.method == "GET":
        return render_template("member_register.html", next=request.args.get("next"))

    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    next_path = request.form.get("next") or "/store"

    if not name or not email or not password:
        return render_template("member_register.html", error="Name, email, and password required", next=next_path), 400
    if len(password) < 8:
        return render_template("member_register.html", error="Password must be at least 8 characters", next=next_path), 400

    try:
        res = requests.post(
            f"{_api_base()}/auth/member/register",
            json={"email": email, "password": password, "name": name},
            timeout=8,
        )
    except requests.RequestException:
        return render_template("member_register.html", error="API unavailable", next=next_path), 502

    if res.status_code not in (200, 201):
        msg = "Email already registered" if res.status_code == 409 else "Could not create account"
        return render_template("member_register.html", error=msg, next=next_path), 400

    token = (res.json() or {}).get("token")
    if not token:
        return render_template("member_register.html", error="Registration failed", next=next_path), 502

    resp = make_response(redirect(next_path))
    resp.set_cookie(MEMBER_COOKIE_NAME, token, httponly=True, samesite="Lax")
    return resp


@app.route("/account/logout", methods=["POST", "GET"])
def account_logout():
    resp = make_response(redirect(url_for("store_homepage")))
    resp.delete_cookie(MEMBER_COOKIE_NAME)
    return resp

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
    return render_template("retailer_portal.html", STRIPE_PUBLIC_KEY=os.getenv("STRIPE_PUBLIC_KEY", ""))


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
