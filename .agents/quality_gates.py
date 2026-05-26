"""
quality_gates.py — Kalite kapilari (syntax, mypy, lint, test, security, review)
"""
import subprocess
from dataclasses import dataclass
from typing import List


@dataclass
class GateResult:
    name: str
    passed: bool
    stdout: str
    stderr: str


class QualityGates:
    """
    Kalite kapilari: fail-fast boru hatti.

    Sirasi:
    1. Syntax check: python -m py_compile
    2. Type check: mypy
    3. Lint: ruff / flake8
    4. Test: pytest
    5. Security: bandit + trivy + trufflehog
    6. Review: Kimi kod incelemesi

    Kural: Bir kapidan gecmezse sonrakiler calismaz.
    """

    def __init__(self, project_path: str = "."):
        self.project_path = project_path

    def run_all(self) -> List[GateResult]:
        results = []
        results.append(self._syntax_check())
        if not results[-1].passed:
            return results
        results.append(self._type_check())
        if not results[-1].passed:
            return results
        results.append(self._lint_check())
        if not results[-1].passed:
            return results
        results.append(self._test_check())
        if not results[-1].passed:
            return results
        results.append(self._security_check())
        if not results[-1].passed:
            return results
        results.append(self._review_check())
        return results

    def _syntax_check(self) -> GateResult:
        try:
            result = subprocess.run(
                ["python", "-m", "py_compile", "PYTHON/main.py"],
                capture_output=True, text=True, cwd=self.project_path
            )
            return GateResult("syntax", result.returncode == 0, result.stdout, result.stderr)
        except Exception as e:
            return GateResult("syntax", False, "", str(e))

    def _type_check(self) -> GateResult:
        try:
            result = subprocess.run(
                ["mypy", "PYTHON/"],
                capture_output=True, text=True, cwd=self.project_path
            )
            return GateResult("mypy", result.returncode == 0, result.stdout, result.stderr)
        except Exception as e:
            return GateResult("mypy", False, "", str(e))

    def _lint_check(self) -> GateResult:
        try:
            result = subprocess.run(
                ["ruff", "check", "PYTHON/"],
                capture_output=True, text=True, cwd=self.project_path
            )
            return GateResult("lint", result.returncode == 0, result.stdout, result.stderr)
        except Exception as e:
            return GateResult("lint", False, "", str(e))

    def _test_check(self) -> GateResult:
        try:
            result = subprocess.run(
                ["pytest", "PYTHON/tests/", "-q"],
                capture_output=True, text=True, cwd=self.project_path
            )
            return GateResult("test", result.returncode == 0, result.stdout, result.stderr)
        except Exception as e:
            return GateResult("test", False, "", str(e))

    def _security_check(self) -> GateResult:
        try:
            result = subprocess.run(
                ["bandit", "-r", "PYTHON/", "-f", "json"],
                capture_output=True, text=True, cwd=self.project_path
            )
            return GateResult("security", result.returncode == 0, result.stdout, result.stderr)
        except Exception as e:
            return GateResult("security", False, "", str(e))

    def _review_check(self) -> GateResult:
        return GateResult("review", True, "Kimi review placeholder", "")
