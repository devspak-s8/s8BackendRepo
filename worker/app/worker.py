# app/worker.py
import os
import json
import shutil
import tempfile
import subprocess
import signal
import sys
from typing import Optional, Tuple
import asyncio

import psutil
import aioboto3
from motor.motor_asyncio import AsyncIOMotorClient

from s8.core.config import settings
from s8.service.template_service import update_template_status

# -----------------------------
# MongoDB (async)
# -----------------------------
mongo_client = AsyncIOMotorClient(settings.MONGO_URL)
db = mongo_client["s8builder"]
template_collection = db["templates"]

# -----------------------------
# AWS async session
# -----------------------------
session = aioboto3.Session()
BUCKET = settings.BUCKET_NAME
REGION = settings.AWS_REGION

async def get_s3_client():
    return await session.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )

async def get_sqs_client():
    return await session.client(
        "sqs",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )

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
async def run_async(cmd, cwd=None, timeout=None, env=None):
    logger.info(f"$ {' '.join(cmd)} (cwd={cwd})")
    env = env or os.environ.copy()
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if stdout:
            logger.info(stdout.decode().strip())
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd, stdout)
        return stdout.decode()
    except asyncio.TimeoutError:
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
    import zipfile
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dst)

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
    return project_dir

async def build_project_if_needed(project_dir: str) -> str:
    framework, guess = detect_framework(project_dir)
    logger.info(f"Detected framework: {framework} (guess out: {guess})")
    out_dir = ensure_build_output(project_dir, framework, guess)

    if framework != "plain":
        env = os.environ.copy()
        has_lock = any(os.path.exists(os.path.join(project_dir, lf)) for lf in ("package-lock.json", "npm-shrinkwrap.json"))
        install_cmd = ["npm", "ci"] if has_lock else ["npm", "install", "--legacy-peer-deps"]
        await run_async(install_cmd, cwd=project_dir, timeout=20*60, env=env)

        pkg = read_package_json(project_dir) or {}
        scripts = pkg.get("scripts", {})

        if framework == "next":
            if "build" in scripts:
                await run_async(["npm", "run", "build"], cwd=project_dir, timeout=30*60, env=env)
            if "export" in scripts:
                await run_async(["npm", "run", "export"], cwd=project_dir, timeout=15*60, env=env)
            else:
                try:
                    await run_async(["npx", "next", "export"], cwd=project_dir, timeout=15*60, env=env)
                except Exception as e:
                    logger.warning(f"next export fallback failed: {e}")
        elif framework in ("vite", "cra", "unknown"):
            await run_async(["npm", "run", "build"], cwd=project_dir, timeout=30*60, env=env)

        out_dir = ensure_build_output(project_dir, framework, guess)

    return out_dir

# -----------------------------
# Async S3 helpers
# -----------------------------
async def upload_folder_to_s3(folder_path: str, s3_prefix: str):
    async with await get_s3_client() as s3_client:
        for root, _, files in os.walk(folder_path):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, folder_path).replace(os.sep, "/")
                key = f"{s3_prefix}/{rel}"
                await s3_client.upload_file(full, BUCKET, key)

async def presign(key: str, expires: int = 3600) -> str:
    async with await get_s3_client() as s3_client:
        return await s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET, "Key": key},
            ExpiresIn=expires,
        )

# -----------------------------
# Semaphore for concurrency control
# -----------------------------
MAX_CONCURRENT_BUILDS = 3
build_semaphore = asyncio.Semaphore(MAX_CONCURRENT_BUILDS)

# -----------------------------
# Template processing
# -----------------------------
async def process_template(template_id: str, upload_zip_key: str):
    async with build_semaphore:
        work_dir = None
        zip_path = None
        try:
            logger.info(f"Processing template {template_id} (zip={upload_zip_key})")
            work_dir = tempfile.mkdtemp(prefix=f"s8builder_{template_id}_")
            zip_path = os.path.join(work_dir, os.path.basename(upload_zip_key))

            async with await get_s3_client() as s3_client:
                await s3_client.download_file(BUCKET, upload_zip_key, zip_path)

            extract_dir = os.path.join(work_dir, "src")
            unzip_to(zip_path, extract_dir)
            entries = [e for e in os.listdir(extract_dir) if not e.startswith(".")]
            if len(entries) == 1 and os.path.isdir(os.path.join(extract_dir, entries[0])):
                extract_dir = os.path.join(extract_dir, entries[0])

            out_dir = await build_project_if_needed(extract_dir)
            logger.info(f"Build complete. Output={out_dir}")

            s3_prefix = f"previews/{template_id}"
            await upload_folder_to_s3(out_dir, s3_prefix)
            preview_key = f"{s3_prefix}/index.html"
            preview_url = await presign(preview_key, expires=3600)
            await update_template_status(template_id, "ready", preview_url)
            logger.info(f"Template {template_id} ready at {preview_url}")

        except Exception as e:
            logger.error(f"Error processing template {template_id}: {e}")
            await update_template_status(template_id, "error", None)
            dlq_url = getattr(settings, "SQS_DLQ_URL", None)
            if dlq_url:
                async with await get_sqs_client() as sqs_client:
                    await sqs_client.send_message(
                        QueueUrl=dlq_url,
                        MessageBody=json.dumps({"template_id": template_id, "s3_key": upload_zip_key})
                    )
        finally:
            if zip_path and os.path.exists(zip_path):
                try: os.remove(zip_path)
                except Exception: pass
            if work_dir: safe_rmtree(work_dir)

# -----------------------------
# Async SQS polling
# -----------------------------
async def poll_sqs():
    logger.info("Starting async SQS polling...")
    async with await get_sqs_client() as sqs_client:
        while not stop_flag:
            try:
                resp = await sqs_client.receive_message(
                    QueueUrl=settings.SQS_QUEUE_URL,
                    MaxNumberOfMessages=5,
                    WaitTimeSeconds=20,
                    VisibilityTimeout=300,
                )
                messages = resp.get("Messages", [])
                if messages:
                    tasks = [
                        process_template(str(json.loads(m["Body"])["template_id"]),
                                         json.loads(m["Body"])["s3_key"])
                        for m in messages
                    ]
                    await asyncio.gather(*tasks)
                    for m in messages:
                        await sqs_client.delete_message(
                            QueueUrl=settings.SQS_QUEUE_URL,
                            ReceiptHandle=m["ReceiptHandle"]
                        )
                else:
                    # Heartbeat log when queue is empty
                    logger.info("SQS queue empty, waiting for new messages...")
                    await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"SQS polling error: {e}")
                await asyncio.sleep(5)



# -----------------------------
# Recover pending templates
# -----------------------------
async def process_stuck_templates():
    pending = [t async for t in template_collection.find({"status": "pending"})]
    if not pending:
        logger.info("No pending templates to process.")
        return

    tasks = []
    for t in pending:
        s3_key = t.get("zip_s3_key")
        if not s3_key:
            logger.warning(f"No zip_s3_key for {t['_id']}")
            continue
        tasks.append(process_template(str(t["_id"]), s3_key))

    if tasks:
        await asyncio.gather(*tasks)
        logger.info(f"Processed {len(tasks)} pending template(s).")

# -----------------------------
# Main loop
# -----------------------------
async def main_loop():
    logger.info("Worker main loop started.")
    try:
        # Recover any stuck templates first
        await process_stuck_templates()

        # Hand off to continuous SQS polling
        await poll_sqs()

    except Exception as e:
        logger.error(f"Worker main loop error: {e}")
        await asyncio.sleep(5)  # backoff on error

# -----------------------------
# Entry point
# -----------------------------
if __name__ == "__main__":
    import asyncio

    async def worker_forever():
        """
        Recover pending templates and continuously poll SQS.
        Loops indefinitely and handles exceptions gracefully.
        """
        global stop_flag
        while not stop_flag:
            try:
                logger.info("Starting recovery of pending templates...")
                await process_stuck_templates()

                logger.info("Starting SQS polling...")
                await poll_sqs()  # this will block and process messages continuously

            except Exception as e:
                logger.error(f"Worker encountered an error: {e}")
                await asyncio.sleep(5)  # backoff before retry

        logger.info("Worker shutdown complete.")

    # Run the worker forever
    asyncio.run(worker_forever())
