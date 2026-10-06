import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

from pipeline import VMConfig, process_video

load_dotenv(Path(__file__).resolve().parent / ".env")

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("vm_server")

app = Flask(__name__)
cfg = VMConfig.from_env()
VM_SECRET = os.getenv("VM_SECRET", "").strip()


@app.before_request
def guard():
    if request.path == "/health":
        return None
    if VM_SECRET and request.headers.get("X-VM-Secret") != VM_SECRET:
        return jsonify({"error": "unauthorized"}), 401
    return None


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/upload")
def upload():
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "file field is required"}), 400
    dest_dir = cfg.output_dir / "uploads"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / Path(file.filename).name
    file.save(dest)
    log.info("Stored upload at %s", dest)
    return jsonify({"path": str(dest)})


@app.post("/process-video")
def process():
    data = request.get_json(silent=True) or {}
    required = ("raw_video_path", "voiceover_path", "output_filename")
    missing = [field for field in required if not data.get(field)]
    if missing:
        return jsonify({"error": f"missing fields: {', '.join(missing)}"}), 400
    try:
        result = process_video(
            data["raw_video_path"], data["voiceover_path"], data["output_filename"], cfg
        )
    except FileNotFoundError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 404
    except Exception as exc:
        log.exception("process-video failed")
        return jsonify({"status": "error", "message": str(exc)}), 500
    return jsonify({"status": "ok", "output_path": str(result)})


@app.get("/download/<path:filename>")
def download(filename):
    target = cfg.output_dir / filename
    if not target.is_file():
        return jsonify({"error": "file not found"}), 404
    return send_from_directory(cfg.output_dir, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(
        host=os.getenv("VM_HOST", "0.0.0.0"),
        port=int(os.getenv("VM_PORT", "5000")),
        threaded=True,
    )
