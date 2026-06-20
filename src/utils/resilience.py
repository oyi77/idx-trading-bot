"""Resilience Engine — Error handling, retry, fallback for IDX Bot."""
import json
import time
import logging
import urllib.request
from pathlib import Path
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("resilience")

WIB = timezone(timedelta(hours=7))
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
CHECKPOINT_DIR = DATA_DIR / "checkpoints"
HEALTH_FILE = DATA_DIR / "health.json"
ERROR_LOG = DATA_DIR / "error_log.json"

CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)


class HealthMonitor:
    """Track system health and send alerts."""
    
    def __init__(self):
        self.errors = []
        self.last_success = None
        self.consecutive_failures = 0
    
    def record_success(self, operation: str):
        self.last_success = datetime.now(WIB).isoformat()
        self.consecutive_failures = 0
    
    def record_failure(self, operation: str, error: str, severity: str = "warning"):
        self.consecutive_failures += 1
        self.errors.append({
            "timestamp": datetime.now(WIB).isoformat(),
            "operation": operation,
            "error": str(error)[:200],
            "severity": severity,
        })
        self.errors = self.errors[-100:]
        
        if self.consecutive_failures >= 3:
            self._send_alert(operation, error, severity)
    
    def _send_alert(self, operation: str, error: str, severity: str):
        try:
            token = __import__('os').environ.get("TELEGRAM_BOT_TOKEN", "")
            admin_id = __import__('os').environ.get("ADMIN_CHAT_ID", "")
            if not token or not admin_id:
                return
            
            msg = f"🚨 <b>VILONA SAHAM — ALERT</b>\nOperation: {operation}\nError: {error[:200]}\nTime: {datetime.now(WIB).strftime('%H:%M WIB')}"
            
            import json as j
            data = j.dumps({"chat_id": admin_id, "text": msg, "parse_mode": "HTML"}).encode()
            req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
        except:
            pass
    
    def is_healthy(self) -> bool:
        return self.consecutive_failures < 5
    
    def get_status(self) -> dict:
        return {
            "healthy": self.is_healthy(),
            "last_success": self.last_success,
            "consecutive_failures": self.consecutive_failures,
            "recent_errors": self.errors[-5:] if self.errors else [],
        }


def check_internet() -> bool:
    """Check internet connectivity."""
    try:
        urllib.request.urlopen("https://www.google.com", timeout=5)
        return True
    except:
        return False


def wait_for_internet(max_wait=300):
    """Wait for internet to return."""
    start = time.time()
    while time.time() - start < max_wait:
        if check_internet():
            return True
        time.sleep(10)
    return False


class CheckpointManager:
    """Save/restore execution state for crash recovery."""
    
    def __init__(self, name: str):
        self.name = name
        self.file = CHECKPOINT_DIR / f"{name}.json"
    
    def save(self, state: dict):
        state['_timestamp'] = datetime.now(WIB).isoformat()
        self.file.write_text(json.dumps(state, indent=2, default=str))
    
    def load(self) -> dict:
        try:
            if self.file.exists():
                return json.loads(self.file.read_text())
        except:
            pass
        return {}
    
    def clear(self):
        if self.file.exists():
            self.file.unlink()


# Global instances
health = HealthMonitor()
