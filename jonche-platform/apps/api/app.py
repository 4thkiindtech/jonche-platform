"""
apps/api/app.py
Jonche Platform — REST API with SQLAlchemy database.
"""

import os
import time
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()


def create_app(config_override=None):
    app = Flask(__name__)

    # ── Config ─────────────────────────────────────────────────────────────────
    db_path = os.getenv("DATABASE_URL", "sqlite:///jonche.db")
    if db_path.startswith("sqlite:///") and not db_path.startswith("sqlite:////"):
        abs_path = os.path.join(os.path.dirname(__file__), db_path.replace("sqlite:///", ""))
        db_path = f"sqlite:///{abs_path}"

    app.config["SQLALCHEMY_DATABASE_URI"] = db_path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

    if config_override:
        app.config.update(config_override)

    # ── Extensions ─────────────────────────────────────────────────────────────
    from db import db
    db.init_app(app)
    CORS(
        app,
        resources={r"/api/*": {"origins": os.getenv("WEB_ORIGIN", "http://localhost:5000")}},
        supports_credentials=True,
    )

    with app.app_context():
        from db import models  # noqa
        db.create_all()

    # ── Lightweight scheduler ─────────────────────────────────────────────────
    # Publishes scheduled drops and ends timeboxed drops without requiring an
    # external cron/worker. Runs at most once every 30 seconds.
    def _run_drop_scheduler():
        from db.models import Drop
        from db import db as _db

        now = datetime.utcnow()

        # Draft → Upcoming if scheduled in the future
        draft_to_upcoming = Drop.query.filter(
            Drop.status == "draft",
            Drop.drop_at.isnot(None),
            Drop.drop_at > now,
        ).update({"status": "upcoming"}, synchronize_session=False)

        # Draft/Upcoming → Live when time hits
        to_live = Drop.query.filter(
            Drop.status.in_(["draft", "upcoming"]),
            Drop.drop_at.isnot(None),
            Drop.drop_at <= now,
        ).update({"status": "live"}, synchronize_session=False)

        # Live → Ended when ends_at passes
        to_ended = Drop.query.filter(
            Drop.status == "live",
            Drop.ends_at.isnot(None),
            Drop.ends_at <= now,
        ).update({"status": "ended"}, synchronize_session=False)

        if draft_to_upcoming or to_live or to_ended:
            _db.session.commit()

    @app.before_request
    def _maybe_run_scheduler():
        last = app.config.get("_LAST_SCHEDULER_RUN", 0.0)
        now_ts = time.time()
        if now_ts - last < 30:
            return
        app.config["_LAST_SCHEDULER_RUN"] = now_ts
        try:
            _run_drop_scheduler()
        except Exception:
            # Scheduler should never break request handling.
            pass

    # ── Blueprints ─────────────────────────────────────────────────────────────
    from routes.drops        import drops_bp
    from routes.members      import members_bp
    from routes.retailers    import retailers_bp
    from routes.analytics    import analytics_bp
    from routes.certificates import certificates_bp
    from routes.stats        import stats_bp
    from routes.auth         import auth_bp
    from routes.waitlist     import waitlist_bp
    from routes.orders       import orders_bp
    from routes.qr           import qr_bp
    from routes.preorders    import preorders_bp
    from routes.payments     import payments_bp
    from routes.notifications import notifications_bp
    from routes.admin        import admin_bp

    app.register_blueprint(auth_bp,          url_prefix="/api/auth")
    app.register_blueprint(drops_bp,         url_prefix="/api/drops")
    app.register_blueprint(members_bp,       url_prefix="/api/members")
    app.register_blueprint(retailers_bp,     url_prefix="/api/retailers")
    app.register_blueprint(analytics_bp,     url_prefix="/api/analytics")
    app.register_blueprint(certificates_bp,  url_prefix="/api/certificates")
    app.register_blueprint(stats_bp,         url_prefix="/api/stats")
    app.register_blueprint(waitlist_bp,      url_prefix="/api/waitlist")
    app.register_blueprint(orders_bp,        url_prefix="/api/orders")
    app.register_blueprint(qr_bp,            url_prefix="/api/qr")
    app.register_blueprint(preorders_bp,     url_prefix="/api/preorders")
    app.register_blueprint(payments_bp,      url_prefix="/api/payments")
    app.register_blueprint(notifications_bp, url_prefix="/api/notifications")
    app.register_blueprint(admin_bp,         url_prefix="/api/admin")

    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "app": "jonche-api"})

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("API_PORT", 5001))
    debug = os.getenv("FLASK_ENV", "development") == "development"
    print(f"🖤 Jonche API running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
