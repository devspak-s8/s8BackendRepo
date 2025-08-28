# app/worker.py
import os
import json
import shutil
import zipfile
import time
import asyncio
import tempfile
import subprocess
import signal
import sys
from typing import Optional, Tuple

import psutil
import boto3
from motor.motor_asyncio import AsyncIOMotorClient

from s8.core.config import settings
from s8.service.template_service import update_template_status

# -----------------------------
# MongoDB (async)
# -----------------------------
mongo_client = AsyncIOMotorClient(settings.MONGO_URL)
db = mongo_client.get_default_database()
template_collection = db["templates"]

# -----------------------------
# AWS clients
# -----------------------------
sqs = boto3.client(
    "sqs",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION,
)
s3 = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION,
)
BUCKET = settings.BUCKET_NAME
REGION = settings.AWS_REGION

# -----------------------------
# Logging
# -----------------------------
import logging
from logging.handlers import RotatingFileHandler

LOG_DIR = "/home/ec2-user/s8Backend/logs"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("s8worker")
logger.setLevel(logging.INFO)
log_file = os.path.join(LOG_DIR, "worker.log")
handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# -----------------------------
# Graceful shutdown
# -----------------------------
stop_flag = False

def handle_shutdown(sig, frame):
    global stop_flag
    logger.info(f"Received shutdown signal: {sig}. Stopping worker...")
    stop_flag = True

signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

# -----------------------------
# Utils
# -----------------------------
def run_with_timeout(cmd, cwd=None, timeout=None, env=None):
    logger.info(f"$ {' '.join(cmd)} (cwd={cwd})")
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )

    try:
        out, _ = proc.communicate(timeout=timeout)
        if out:
            logger.info(out.strip())
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd, out)
        return out
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout} seconds: {' '.join(cmd)}")
        parent = psutil.Process(proc.pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
        raise RuntimeError(f"Timeout expired for command: {' '.join(cmd)}")

def safe_rmtree(path: str):
    try:
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)
    except Exception as e:
        logger.warning(f"Cleanup warning for {path}: {e}")

def unzip_to(zip_path: str, dst: str):
    safe_rmtree(dst)
    os.makedirs(dst, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dst)

def upload_folder_to_s3(folder_path: str, s3_prefix: str):
    for root, _, files in os.walk(folder_path):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, folder_path).replace(os.sep, "/")
            key = f"{s3_prefix}/{rel}"
            s3.upload_file(full, BUCKET, key)

def presign(key: str, expires: int = 3600) -> str:
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": key},
        ExpiresIn=expires,
    )

def read_package_json(path: str) -> Optional[dict]:
    pj = os.path.join(path, "package.json")
    if not os.path.exists(pj):
        return None
    try:
        with open(pj, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read package.json: {e}")
        return None

def detect_framework(project_dir: str) -> Tuple[str, Optional[str]]:
    pkg = read_package_json(project_dir)
    if not pkg:
        return "plain", None
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    if "next" in deps:
        return "next", None
    if "vite" in deps:
        return "vite", None
    if "react" in deps:
        return "cra", None
    for guess in ("dist", "build", "out"):
        if os.path.exists(os.path.join(project_dir, guess)):
            return "unknown", guess
    return "plain", None

def ensure_build_output(project_dir: str, framework: str, guessed_dir: Optional[str]) -> Optional[str]:
    if guessed_dir:
        p = os.path.join(project_dir, guessed_dir)
        if os.path.exists(p):
            return p
    for guess in ("build", "dist", "out"):
        p = os.path.join(project_dir, guess)
        if os.path.exists(p):
            return p
    # For plain / Next.js projects without index.html, just return project_dir
    return project_dir

# -----------------------------
# Build & publish
# -----------------------------
def build_project_if_needed(project_dir: str) -> str:
    framework, guess = detect_framework(project_dir)
    logger.info(f"Detected framework: {framework} (guess out: {guess})")
    out_dir = ensure_build_output(project_dir, framework, guess)

    if framework != "plain":
        env = os.environ.copy()
        has_lock = any(os.path.exists(os.path.join(project_dir, lf)) for lf in ("package-lock.json", "npm-shrinkwrap.json"))
        install_cmd = ["npm", "ci"] if has_lock else ["npm", "install", "--legacy-peer-deps"]
        run_with_timeout(install_cmd, cwd=project_dir, timeout=20*60, env=env)

        pkg = read_package_json(project_dir) or {}
        scripts = pkg.get("scripts", {})
        if framework == "next":
            if "build" in scripts:
                run_with_timeout(["npm", "run", "build"], cwd=project_dir, timeout=30*60, env=env)
            if "export" in scripts:
                run_with_timeout(["npm", "run", "export"], cwd=project_dir, timeout=15*60, env=env)
            else:
                try:
                    run_with_timeout(["npx", "next", "export"], cwd=project_dir, timeout=15*60, env=env)
                except Exception as e:
                    logger.warning(f"next export fallback failed: {e}")
        elif framework in ("vite", "cra", "unknown"):
            run_with_timeout(["npm", "run", "build"], cwd=project_dir, timeout=30*60, env=env)

        out_dir = ensure_build_output(project_dir, framework, guess)

    return out_dir

async def process_template(template_id: str, upload_zip_key: str):
    work_dir = None
    zip_path = None
    try:
        logger.info(f"Processing template {template_id} (zip={upload_zip_key})")
        work_dir = tempfile.mkdtemp(prefix=f"s8builder_{template_id}_")
        zip_path = os.path.join(work_dir, os.path.basename(upload_zip_key))
        s3.download_file(BUCKET, upload_zip_key, zip_path)

        extract_dir = os.path.join(work_dir, "src")
        unzip_to(zip_path, extract_dir)
        entries = [e for e in os.listdir(extract_dir) if not e.startswith(".")]
        if len(entries) == 1 and os.path.isdir(os.path.join(extract_dir, entries[0])):
            extract_dir = os.path.join(extract_dir, entries[0])

        out_dir = build_project_if_needed(extract_dir)
        logger.info(f"Build complete. Output={out_dir}")

        s3_prefix = f"previews/{template_id}"
        upload_folder_to_s3(out_dir, s3_prefix)
        preview_key = f"{s3_prefix}/index.html"
        preview_url = presign(preview_key, expires=3600)
        await update_template_status(template_id, "ready", preview_url)
        logger.info(f"Template {template_id} ready at {preview_url}")

    except Exception as e:
        logger.error(f"Error processing template {template_id}: {e}")
        await update_template_status(template_id, "error", None)
        # Optional DLQ
        dlq_url = getattr(settings, "SQS_DLQ_URL", None)
        if dlq_url:
            logger.info(f"Sending failed template {template_id} to DLQ")
            sqs.send_message(
                QueueUrl=dlq_url,
                MessageBody=json.dumps({"template_id": template_id, "s3_key": upload_zip_key})
            )
    finally:
        if zip_path and os.path.exists(zip_path):
            try: os.remove(zip_path)
            except Exception: pass
        if work_dir: safe_rmtree(work_dir)

# -----------------------------
# Poll SQS (async)
# -----------------------------
async def poll_sqs():
    logger.info("Starting SQS polling...")
    while not stop_flag:
        try:
            resp = sqs.receive_message(
                QueueUrl=settings.SQS_QUEUE_URL,
                MaxNumberOfMessages=5,
                WaitTimeSeconds=20,
                VisibilityTimeout=300,
            )
            messages = resp.get("Messages", [])
            if messages:
                await asyncio.gather(*(process_template(json.loads(m["Body"])["template_id"],
                                                          json.loads(m["Body"])["s3_key"])
                                       for m in messages))
                for m in messages:
                    sqs.delete_message(
                        QueueUrl=settings.SQS_QUEUE_URL,
                        ReceiptHandle=m["ReceiptHandle"]
                    )
            else:
                await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"SQS polling error: {e}")
            await asyncio.sleep(5)

# -----------------------------
# Recover pending templates
# -----------------------------
async def process_stuck_templates():
    pending = [t async for t in template_collection.find({"status": "pending"})]
    tasks = []
    for t in pending:
        s3_key = t.get("zip_s3_key")
        if not s3_key:
            logger.warning(f"No zip_s3_key for {t['_id']}")
            continue
        tasks.append(process_template(str(t["_id"]), s3_key))
    if tasks:
        await asyncio.gather(*tasks)

# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(process_stuck_templates())
        loop.run_until_complete(poll_sqs())
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
    finally:
        logger.info("Worker shutdown complete.")
        loop.close()
        sys.exit(0)