"""
rollback_system.py — Git tabanli anlik kaydet / geri al sistemi
"""
import subprocess
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Snapshot:
    commit_hash: str
    branch: str
    message: str
    timestamp: str


class RollbackSystem:
    """
    Git tabanli anlik kaydet / geri al sistemi.

    Surec:
    1. Degisiklik oncesi: snapshot al
    2. Degisiklik sonrasi: eger testler basarisizsa otomatik geri al
    3. Rollback: git checkout > stash > git reset --hard > geri al

    Kullanim:
        rb = RollbackSystem()
        snap = rb.snapshot("HFT router ekleme")
        # degisiklikler ...
        if not tests_pass:
            rb.rollback(snap)
    """

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path

    def snapshot(self, message: str) -> Snapshot:
        ts = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=self.repo_path
        ).stdout.strip()
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, cwd=self.repo_path
        ).stdout.strip()
        return Snapshot(commit_hash=ts, branch=branch, message=message, timestamp="")

    def rollback(self, snapshot: Snapshot) -> bool:
        subprocess.run(["git", "stash"], cwd=self.repo_path)
        result = subprocess.run(
            ["git", "reset", "--hard", snapshot.commit_hash],
            capture_output=True, text=True, cwd=self.repo_path
        )
        return result.returncode == 0

    def list_snapshots(self, n: int = 10) -> List[Snapshot]:
        result = subprocess.run(
            ["git", "log", "--oneline", f"-{n}"],
            capture_output=True, text=True, cwd=self.repo_path
        )
        lines = result.stdout.strip().split("\n")
        snapshots = []
        for line in lines:
            parts = line.split(" ", 1)
            if len(parts) == 2:
                snapshots.append(Snapshot(commit_hash=parts[0], branch="", message=parts[1], timestamp=""))
        return snapshots
