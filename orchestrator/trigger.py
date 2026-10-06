import logging
import time
from datetime import datetime

from flask import Flask, jsonify, request

from .config import Settings
from .pipeline import run_pipeline

log = logging.getLogger(__name__)


def run_scheduler(settings: Settings) -> None:
    days = set(settings.cron_days)
    log.info("Scheduler armed | days=%s time=%s", sorted(days), settings.cron_time)
    last_run_date = ""
    while True:
        now = datetime.now()
        if (
            now.strftime("%A").lower() in days
            and now.strftime("%H:%M") == settings.cron_time
            and now.date().isoformat() != last_run_date
        ):
            last_run_date = now.date().isoformat()
            log.info("Cron trigger fired")
            try:
                run_pipeline(settings=settings)
            except Exception:
                log.exception("Scheduled pipeline run failed")
        time.sleep(20)


def run_webhook(settings: Settings) -> None:
    app = Flask("bigpikle-trigger")

    @app.post("/trigger")
    def trigger():
        if settings.webhook_secret and request.headers.get("X-Webhook-Secret") != settings.webhook_secret:
            return jsonify({"error": "unauthorized"}), 401
        data = request.get_json(silent=True) or {}
        try:
            result = run_pipeline(topic=data.get("topic"), settings=settings)
        except Exception as exc:
            log.exception("Webhook pipeline run failed")
            return jsonify({"status": "error", "message": str(exc)}), 500
        return jsonify({"status": "ok", "result": result})

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    log.info("Webhook listening on http://%s:%d/trigger", settings.webhook_host, settings.webhook_port)
    app.run(host=settings.webhook_host, port=settings.webhook_port, threaded=True)
