"""
benchmarks/report_generator.py — Benchmark rapor ureticisi
"""
from datetime import datetime
from pathlib import Path


class BenchmarkReport:
    """
    GPU/CPU benchmark raporunu Markdown/JSON olarak uretir.

    K186: Her benchmark sonucu tarihli olarak arsivlenir.
    """

    def __init__(self, output_dir: str = "DATA/benchmarks"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, results: dict) -> str:
        timestamp = datetime.utcnow().isoformat()
        lines = [
            "# Benchmark Raporu",
            f"Tarih: {timestamp}",
            "",
            "| Metrik | Deger |",
            "|--------|-------|",
        ]
        for k, v in results.items():
            lines.append(f"| {k} | {v} |")
        md = "\n".join(lines)
        file_path = self.output_dir / f"benchmark_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
        file_path.write_text(md, encoding="utf-8")
        return str(file_path)
