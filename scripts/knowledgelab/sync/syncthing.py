"""Syncthing integration: check availability and status."""
from __future__ import annotations

import json
import urllib.request


SYNCTHING_API = "http://127.0.0.1:8384/rest"


def is_syncthing_available(timeout: int = 3) -> bool:
    """Check if Syncthing is running locally."""
    try:
        request = urllib.request.Request(
            f"{SYNCTHING_API}/system/status",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read(10_000).decode("utf-8"))
            return bool(data.get("myID"))
    except Exception:
        return False


def syncthing_status(timeout: int = 5) -> dict:
    """Get Syncthing status summary."""
    if not is_syncthing_available(timeout):
        return {
            "available": False,
            "message": "Syncthing не запущен. Установите с https://syncthing.net/ и запустите.",
        }

    try:
        request = urllib.request.Request(
            f"{SYNCTHING_API}/system/status",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = json.loads(response.read(10_000).decode("utf-8"))

        folders_request = urllib.request.Request(
            f"{SYNCTHING_API}/config/folders",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(folders_request, timeout=timeout) as response:
            folders = json.loads(response.read(50_000).decode("utf-8"))

        return {
            "available": True,
            "device_name": status.get("computerName", ""),
            "folders": len(folders),
            "folder_names": [f.get("label", f.get("id", "")) for f in folders[:5]],
            "message": f"Syncthing запущен. {len(folders)} папок синхронизируется.",
        }
    except Exception as exc:
        return {
            "available": True,
            "message": f"Syncthing запущен, но не удалось получить статус: {exc}",
        }


def syncthing_setup_instructions() -> str:
    """Return setup instructions for Syncthing."""
    return """\
Для синхронизации vault между устройствами через Syncthing:

1. Скачайте Syncthing: https://syncthing.net/downloads/
2. Запустите Syncthing на обоих устройствах
3. Откройте веб-интерфейс: http://127.0.0.1:8384
4. На первом устройстве: Actions → Show ID → скопируйте ID
5. На втором устройстве: Add Remote Device → вставьте ID первого
6. На первом устройстве: Add Folder → выберите папку vault → разрешите второму устройству
7. Vault автоматически синхронизируется между устройствами

Syncthing бесплатный, P2P, без облака. Данные не покидают ваши устройства."""
