"""Configure an application-local bridge secret. Never copies Codex credentials."""

from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[1]
path = root / ".env"
lines = path.read_text(encoding="utf-8-sig").splitlines() if path.exists() else []
values = {
    line.split("=", 1)[0].strip(): line.split("=", 1)[1].strip()
    for line in lines
    if "=" in line and not line.lstrip().startswith("#")
}
updates = {
    "LLM_PROVIDER": "codex",
    "CODEX_BRIDGE_URL": "http://host.docker.internal:8866",
    "CODEX_BRIDGE_TOKEN": (
        values.get("CODEX_BRIDGE_TOKEN")
        if len(values.get("CODEX_BRIDGE_TOKEN", "")) >= 32
        else secrets.token_urlsafe(40)
    ),
}
retained = [line for line in lines if line.split("=", 1)[0].strip() not in updates]
path.write_text(
    "\n".join(retained + [f"{k}={v}" for k, v in updates.items()]) + "\n",
    encoding="utf-8",
)
(root / ".private").mkdir(exist_ok=True)
print(
    "Configured Codex bridge in ignored .env. Codex sign-in credentials were not read or copied."
)
