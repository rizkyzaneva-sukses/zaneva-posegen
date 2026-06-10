import os
import uuid
import json
import shutil
import zipfile
import threading
import time
import logging
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty

from flask import (
    Flask, render_template, request, session, redirect,
    url_for, jsonify, Response, send_file, flash
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "zaneva-posegen-secret-2024")

APP_PASSWORD = os.environ.get("APP_PASSWORD", "zaneva2024")
SA_PATH = os.path.join(os.path.dirname(__file__), "config", "service-account.json")
TMP_DIR = os.path.join(os.path.dirname(__file__), "tmp_posegen")

os.makedirs(os.path.join(os.path.dirname(__file__), "config"), exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

# SSE event queues per session_id
_sse_queues: dict[str, Queue] = {}

# Status generate per session_id
_gen_status: dict[str, dict] = {}


# ── Helpers ──────────────────────────────────────────────────────────────────

def is_sa_configured() -> bool:
    return os.path.exists(SA_PATH)


def init_vertex_if_needed():
    """Init Vertex AI dari SA file jika belum."""
    from modules import vertex_client
    if is_sa_configured() and not vertex_client.is_initialized():
        try:
            vertex_client.init_from_file(SA_PATH)
        except Exception as e:
            logger.error(f"Gagal init Vertex AI: {e}")


def get_session_dir(session_id: str) -> Path:
    p = Path(TMP_DIR) / session_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def cleanup_old_sessions():
    """Hapus session > 48 jam."""
    now = time.time()
    for d in Path(TMP_DIR).iterdir():
        if d.is_dir():
            age = now - d.stat().st_mtime
            if age > 48 * 3600:
                shutil.rmtree(d, ignore_errors=True)


# ── Auth guards ───────────────────────────────────────────────────────────────

@app.before_request
def guard():
    open_routes = {"login", "setup", "static"}
    if request.endpoint in open_routes:
        return
    if not is_sa_configured():
        return redirect(url_for("setup"))
    if not session.get("logged_in"):
        return redirect(url_for("login"))


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == APP_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        flash("Password salah")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Setup routes ──────────────────────────────────────────────────────────────

@app.route("/setup", methods=["GET", "POST"])
def setup():
    status = None
    project_id = None

    if request.method == "POST":
        f = request.files.get("sa_file")
        if not f or not f.filename.endswith(".json"):
            flash("Upload file .json yang valid")
            return render_template("setup.html", status=status)

        # Validasi isi JSON
        try:
            content = f.read()
            sa_info = json.loads(content)
            if "project_id" not in sa_info or "type" not in sa_info:
                flash("File bukan Service Account JSON yang valid")
                return render_template("setup.html", status=status)
        except Exception:
            flash("File JSON tidak valid")
            return render_template("setup.html", status=status)

        # Simpan ke config/
        os.makedirs(os.path.dirname(SA_PATH), exist_ok=True)
        with open(SA_PATH, "wb") as out:
            out.write(content)

        # Test koneksi
        from modules import vertex_client
        try:
            vertex_client.init_from_file(SA_PATH)
            result = vertex_client.test_connection()
            if result["ok"]:
                status = "ok"
                project_id = result["project_id"]
            else:
                status = "error"
                flash(f"Koneksi gagal: {result['error']}")
        except Exception as e:
            status = "error"
            flash(f"Error: {str(e)}")

    return render_template("setup.html", status=status, project_id=project_id,
                           already_configured=is_sa_configured())


# ── Main routes ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    init_vertex_if_needed()
    cleanup_old_sessions()
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    """Upload 1-5 foto produk, return file_ids."""
    files = request.files.getlist("photos")
    if not files or len(files) > 5:
        return jsonify({"error": "Upload 1-5 foto"}), 400

    session_id = session.get("gen_session_id") or str(uuid.uuid4())
    session["gen_session_id"] = session_id

    sess_dir = get_session_dir(session_id)
    input_dir = sess_dir / "input"
    input_dir.mkdir(exist_ok=True)

    saved = []
    for i, f in enumerate(files):
        if not f.filename:
            continue
        ext = Path(f.filename).suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            return jsonify({"error": f"Format {ext} tidak didukung"}), 400

        # Cek ukuran (max 10MB)
        f.seek(0, 2)
        size = f.tell()
        f.seek(0)
        if size > 10 * 1024 * 1024:
            return jsonify({"error": f"File {f.filename} melebihi 10MB"}), 400

        filename = f"product_{i+1}{ext}"
        save_path = input_dir / filename
        f.save(str(save_path))
        saved.append({"id": filename, "name": f.filename})

    return jsonify({"session_id": session_id, "files": saved})


@app.route("/generate", methods=["POST"])
def generate():
    """Mulai generate 25 pose di background thread."""
    data = request.json or {}
    session_id = session.get("gen_session_id")
    if not session_id:
        return jsonify({"error": "Belum ada upload"}), 400

    product_name = data.get("product_name", "Produk").strip() or "Produk"
    body_type = data.get("body_type", "average")
    background = data.get("background", "putih")

    # Cek input files ada
    input_dir = get_session_dir(session_id) / "input"
    input_files = list(input_dir.glob("*"))
    if not input_files:
        return jsonify({"error": "Foto produk tidak ditemukan"}), 400

    # Simpan config ke session
    session["product_name"] = product_name
    session["body_type"] = body_type
    session["background"] = background

    # Init status
    from modules.pose_engine import POSE_ORDER
    _gen_status[session_id] = {
        pid: {"status": "pending", "url": None, "error": None}
        for pid in POSE_ORDER
    }

    # SSE queue
    _sse_queues[session_id] = Queue()

    # Start background thread
    t = threading.Thread(
        target=_run_generate,
        args=(session_id, str(input_files[0]), product_name, body_type, background),
        daemon=True
    )
    t.start()

    return jsonify({"ok": True, "session_id": session_id})


def _run_generate(session_id: str, garment_path: str, product_name: str,
                  body_type: str, background: str):
    """Background thread: generate 25 pose satu per satu."""
    from modules import vertex_client
    from modules.pose_engine import POSE_ORDER, build_prompt

    sess_dir = get_session_dir(session_id)
    output_dir = sess_dir / "output"
    output_dir.mkdir(exist_ok=True)

    q = _sse_queues.get(session_id)
    total = len(POSE_ORDER)

    for i, pose_id in enumerate(POSE_ORDER):
        _gen_status[session_id][pose_id]["status"] = "processing"
        _push_event(q, "pose_start", {"pose_id": pose_id, "index": i + 1, "total": total})

        try:
            prompt = build_prompt(pose_id, body_type, background)
            img_bytes = vertex_client.generate_image(garment_path, prompt)

            # Tentukan subfolder
            group = pose_id[0]
            group_dirs = {
                "A": "A_standing", "B": "B_sports",
                "C": "C_casual", "D": "D_detail", "E": "E_candid"
            }
            subdir = output_dir / group_dirs.get(group, group)
            subdir.mkdir(exist_ok=True)

            # Nama file output
            safe_name = product_name.replace(" ", "_")[:30]
            out_filename = f"{safe_name}_{pose_id}.jpg"
            out_path = subdir / out_filename
            with open(str(out_path), "wb") as f:
                f.write(img_bytes)

            rel_path = f"/output/{session_id}/{group_dirs.get(group, group)}/{out_filename}"
            _gen_status[session_id][pose_id]["status"] = "done"
            _gen_status[session_id][pose_id]["url"] = rel_path
            _push_event(q, "pose_done", {
                "pose_id": pose_id, "url": rel_path,
                "index": i + 1, "total": total
            })

        except Exception as e:
            logger.error(f"Pose {pose_id} gagal: {e}")
            _gen_status[session_id][pose_id]["status"] = "failed"
            _gen_status[session_id][pose_id]["error"] = str(e)
            _push_event(q, "pose_failed", {
                "pose_id": pose_id, "error": str(e),
                "index": i + 1, "total": total
            })

    _push_event(q, "generate_complete", {"total": total})


def _push_event(q: Queue, event: str, data: dict):
    if q:
        q.put({"event": event, "data": data})


@app.route("/progress/<session_id>")
def progress(session_id: str):
    """SSE endpoint untuk real-time progress."""
    if session.get("gen_session_id") != session_id:
        return Response("Unauthorized", status=403)

    def stream():
        q = _sse_queues.get(session_id)
        if not q:
            yield f"event: error\ndata: {{\"msg\": \"Session tidak ditemukan\"}}\n\n"
            return
        while True:
            try:
                msg = q.get(timeout=30)
                yield f"event: {msg['event']}\ndata: {json.dumps(msg['data'])}\n\n"
                if msg["event"] == "generate_complete":
                    break
            except Empty:
                yield "event: ping\ndata: {}\n\n"

    return Response(stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/status/<session_id>")
def status(session_id: str):
    """Return status semua 25 pose."""
    if session.get("gen_session_id") != session_id:
        return jsonify({"error": "Unauthorized"}), 403
    return jsonify(_gen_status.get(session_id, {}))


@app.route("/retry/<session_id>/<pose_id>", methods=["POST"])
def retry_pose(session_id: str, pose_id: str):
    """Regenerate satu pose yang gagal."""
    if session.get("gen_session_id") != session_id:
        return jsonify({"error": "Unauthorized"}), 403

    from modules import vertex_client
    from modules.pose_engine import build_prompt, POSE_ORDER

    if pose_id not in POSE_ORDER:
        return jsonify({"error": "Pose tidak valid"}), 400

    input_dir = get_session_dir(session_id) / "input"
    input_files = list(input_dir.glob("*"))
    if not input_files:
        return jsonify({"error": "Input tidak ditemukan"}), 400

    body_type = session.get("body_type", "average")
    background = session.get("background", "putih")
    product_name = session.get("product_name", "Produk")

    try:
        prompt = build_prompt(pose_id, body_type, background)
        img_bytes = vertex_client.generate_image(str(input_files[0]), prompt)

        group = pose_id[0]
        group_dirs = {
            "A": "A_standing", "B": "B_sports",
            "C": "C_casual", "D": "D_detail", "E": "E_candid"
        }
        subdir = get_session_dir(session_id) / "output" / group_dirs.get(group, group)
        subdir.mkdir(exist_ok=True)

        safe_name = product_name.replace(" ", "_")[:30]
        out_filename = f"{safe_name}_{pose_id}.jpg"
        out_path = subdir / out_filename
        with open(str(out_path), "wb") as f:
            f.write(img_bytes)

        rel_path = f"/output/{session_id}/{group_dirs.get(group, group)}/{out_filename}"
        if session_id in _gen_status and pose_id in _gen_status[session_id]:
            _gen_status[session_id][pose_id]["status"] = "done"
            _gen_status[session_id][pose_id]["url"] = rel_path
            _gen_status[session_id][pose_id]["error"] = None

        return jsonify({"ok": True, "url": rel_path})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/output/<session_id>/<path:filename>")
def serve_output(session_id: str, filename: str):
    """Serve generated images."""
    if session.get("gen_session_id") != session_id:
        return "Unauthorized", 403
    file_path = Path(TMP_DIR) / session_id / "output" / filename
    if not file_path.exists():
        return "Not found", 404
    return send_file(str(file_path), mimetype="image/jpeg")


@app.route("/download-all/<session_id>")
def download_all(session_id: str):
    """Download semua output sebagai ZIP."""
    if session.get("gen_session_id") != session_id:
        return "Unauthorized", 403

    product_name = session.get("product_name", "Produk").replace(" ", "_")[:30]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"{product_name}_poses_{timestamp}.zip"
    zip_path = Path(TMP_DIR) / session_id / zip_name

    output_dir = Path(TMP_DIR) / session_id / "output"
    if not output_dir.exists():
        return "Belum ada output", 404

    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        for file in output_dir.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(output_dir)
                zf.write(str(file), str(arcname))

    return send_file(
        str(zip_path),
        mimetype="application/zip",
        as_attachment=True,
        download_name=zip_name
    )


if __name__ == "__main__":
    init_vertex_if_needed()
    app.run(host="0.0.0.0", port=5003, debug=False)
