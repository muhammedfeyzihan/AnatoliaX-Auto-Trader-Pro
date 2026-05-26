"""
automation/deploy_pipeline.py — Otomatik deploy pipeline
"""
from pathlib import Path
from typing import List


class DeployPipeline:
    """
    Otomatik deploy pipeline.

    Asamalar:
    1. Git tag + versiyon
    2. Test calistirma (pytest + jest)
    3. Docker image build
    4. GitHub release
    5. Sunucu uzerine rolling deploy

    K205: Deploy sadece tum testler gectiginde ve Human Gate L3 onayinda yapilir.
    """

    def __init__(self, project_root: str = "."):
        self.root = Path(project_root)

    def run_tests(self) -> bool:
        import subprocess
        try:
            subprocess.run(["pytest", "PYTHON/tests/"], cwd=str(self.root), check=True)
            return True
        except Exception:
            return False

    def build_docker(self) -> bool:
        import subprocess
        try:
            subprocess.run(["docker", "build", "-t", "anatoliax:latest", "."], cwd=str(self.root), check=True)
            return True
        except Exception:
            return False
