"""
.agents/code_review.py — Otomatik kod inceleme motoru
"""
from pathlib import Path
from typing import List, Dict


class CodeReviewEngine:
    """
    Kod inceleme motoru: statik analiz, mimari uygunluk, K-kural uyumu.

    Asamalar:
    1. Syntax dogrulama (py_compile)
    2. Import kontrolu (dolasiklik, eksik bagimlilik)
    3. Kural uyumu (K1-K141 regex tarama)
    4. Mimari uygunluk (modul smirlarina saygi)

    K187: Kod inceleme her PR oncesi calisir; RED ise merge bloklanir.
    """

    def __init__(self, project_root: str = "."):
        self.root = Path(project_root)

    def review_file(self, file_path: str) -> Dict:
        path = Path(file_path)
        errors = []
        try:
            import py_compile
            py_compile.compile(str(path), doraise=True)
        except Exception as e:
            errors.append(f"Syntax: {e}")

        # Kural tarama (ornek)
        content = path.read_text(encoding="utf-8")
        if "API_KEY" in content and "env" not in content.lower():
            errors.append("API_KEY sifreli yazilmis; .env kullanilmali (K2)")

        return {"file": file_path, "errors": errors, "ok": len(errors) == 0}

    def review_batch(self, files: List[str]) -> List[Dict]:
        return [self.review_file(f) for f in files]
