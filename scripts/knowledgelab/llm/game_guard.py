"""GPU Game Guard — snapshot collection and heavy-load detection."""
from __future__ import annotations

import json
import subprocess

from knowledgelab.config import ROOT


def collect_gpu_snapshot_script() -> str:
    return r"""
$ErrorActionPreference = 'SilentlyContinue'
$samples = @()
try {
  $samples = (Get-Counter '\GPU Engine(*)\Utilization Percentage').CounterSamples |
    Where-Object { $_.CookedValue -gt 2 } |
    ForEach-Object {
      $pidValue = $null
      if ($_.InstanceName -match 'pid_([0-9]+)_') { $pidValue = [int]$Matches[1] }
      [pscustomobject]@{ pid=$pidValue; value=[math]::Round($_.CookedValue, 1); instance=$_.InstanceName }
    }
} catch {}
$groups = @()
foreach ($group in ($samples | Where-Object { $_.pid } | Group-Object pid)) {
  $pidValue = [int]$group.Name
  $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
  if ($proc) {
    $groups += [pscustomobject]@{
      pid=$pidValue
      name=$proc.ProcessName
      gpu=[math]::Round((($group.Group | Measure-Object value -Sum).Sum), 1)
    }
  }
}
$nvidia = Get-Command nvidia-smi -ErrorAction SilentlyContinue
$gpuTotal = 0
$memory = ''
if ($nvidia) {
  $line = & $nvidia.Source --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>$null | Select-Object -First 1
  if ($line -match '^\s*([0-9]+)\s*,\s*([0-9]+)\s*,\s*([0-9]+)') {
    $gpuTotal = [int]$Matches[1]
    $memory = "$($Matches[2])/$($Matches[3]) MB"
  }
}
$labNames = @('LM Studio','lms','python','pythonw')
$lab = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $labNames -contains $_.ProcessName } | Select-Object -First 12 | ForEach-Object {
  [pscustomobject]@{ pid=$_.Id; name=$_.ProcessName }
})
[pscustomobject]@{ gpu_total=$gpuTotal; memory=$memory; processes=$groups; lab=$lab } | ConvertTo-Json -Depth 5
""".strip()


def collect_gpu_snapshot() -> dict:
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        collect_gpu_snapshot_script(),
    ]
    try:
        result = subprocess.run(
            command,
            cwd=str(ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=12,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return json.loads(result.stdout or "{}")
    except Exception:
        return {}


def is_gpu_snapshot_heavy(snapshot: dict) -> bool:
    try:
        total = int(snapshot.get("gpu_total") or 0)
    except (TypeError, ValueError):
        total = 0
    if total >= 45:
        return True
    processes = snapshot.get("processes") or []
    if isinstance(processes, dict):
        processes = [processes]
    for process in processes:
        try:
            if float(process.get("gpu") or 0) >= 20:
                return True
        except (TypeError, ValueError):
            continue
    return False
