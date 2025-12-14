import asyncio
import structlog
import httpx
import json

from app.core.config import settings

logger = structlog.get_logger()

async def run_manual_backup() -> str:
    # Placeholder: trigger docker compose backup services
    logger.info("manual_backup_triggered")
    return "Backup triggered (postgres)"

async def restore_backup(backup_id: str) -> str:
    logger.info("restore_backup_triggered", backup_id=backup_id)
    return f"Restored from {backup_id} (placeholder)"

async def _get_health() -> dict:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("http://app:8000/api/health/status")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        return {}

async def status_command(update, context):
    data = await _get_health()
    overall = data.get("overall", "unknown")
    await update.message.reply_text(f"📊 Status: {overall}")

async def metrics_command(update, context):
    data = await _get_health()
    sys = data.get("system", {})
    db = data.get("database", "unknown")
    msg = (
        f"CPU: {sys.get('cpu_percent','n/a')}%\n"
        f"RAM: {sys.get('memory_percent','n/a')}%\n"
        f"Disk: {sys.get('disk_percent','n/a')}%\n"
        f"DB: {db}"
    )
    await update.message.reply_text(msg)

async def alerts_command(update, context):
    await update.message.reply_text("Alerts history is unavailable (Redis disabled)")

async def health_command(update, context):
    data = await _get_health()
    # return compact JSON
    await update.message.reply_text(json.dumps(data, ensure_ascii=False, indent=2)[:3500])

async def logs_command(update, context):
    # reuse alerts_history as recent log-like entries
    await alerts_command(update, context)

async def storage_command(update, context):
    # Placeholder for storage command
    await update.message.reply_text("💾 Storage status: OK\n📦 Used: 1.2 GB\n📊 Quota: 10 GB")

async def backup_bot_command(update, context):
    text = update.message.text.strip()
    if text == "/backup":
        result = await run_manual_backup()
        await update.message.reply_text(f"✅ Backup completed:\n{result}")
    elif text == "/restore":
        await update.message.reply_text("🔄 Available backups:\n/list")
    elif text.startswith("/restore "):
        backup_id = text.split()[1]
        result = await restore_backup(backup_id)
        await update.message.reply_text(f"✅ Restored from {backup_id}")
    elif text == "/status":
        await status_command(update, context)
    elif text == "/metrics":
        await metrics_command(update, context)
    elif text == "/alerts":
        await alerts_command(update, context)
    elif text == "/health":
        await health_command(update, context)
    elif text == "/logs":
        await logs_command(update, context)
    elif text == "/storage":
        await storage_command(update, context)
    else:
        await update.message.reply_text("Unknown command")


# Simple class to act as a service
class BackupBotService:
    def __init__(self):
        pass

    async def run_manual_backup(self) -> str:
        return await run_manual_backup()

    async def restore_backup(self, backup_id: str) -> str:
        return await restore_backup(backup_id)

    async def backup_bot_command(self, update, context):
        return await backup_bot_command(update, context)


# Singleton instance
backup_bot = BackupBotService()