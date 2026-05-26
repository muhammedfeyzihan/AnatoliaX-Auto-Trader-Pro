"""
agent_scoring.py — Her ajanin tahmin dogrulugu skoru
"""
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List


class AgentScorer:
    """Ajan performans takibi."""

    SCORE_FILE = "agent_scores.jsonl"

    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.getenv("DATA_DIR", ".")
        self.score_path = os.path.join(self.data_dir, self.SCORE_FILE)
        self.records: List[Dict] = []
        self._load()

    def _load(self):
        if os.path.exists(self.score_path):
            with open(self.score_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.records.append(json.loads(line))

    def record_prediction(
        self,
        agent: str,
        symbol: str,
        prediction: str,  # AL, SAT, BEKLE
        actual: str,      # YUKSEL, DUS, DUZ
        confidence: float = 0.0,
    ) -> Dict:
        """Ajan tahminini kaydeder."""
        # Tahmin -> gerceklesme eslestirmesi
        correct = False
        if prediction == "AL" and actual == "YUKSEL":
            correct = True
        elif prediction == "SAT" and actual == "DUS":
            correct = True
        elif prediction == "BEKLE" and actual == "DUZ":
            correct = True

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent.upper(),
            "symbol": symbol.upper(),
            "prediction": prediction,
            "actual": actual,
            "confidence": confidence,
            "correct": correct,
        }
        self.records.append(record)
        with open(self.score_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def calculate_score(self, agent: str = None, days: int = 30) -> Dict:
        """Ajan(lar)in performans skorunu hesaplar."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        filtered = [
            r for r in self.records
            if datetime.fromisoformat(r["timestamp"]) >= cutoff
            and (agent is None or r["agent"] == agent.upper())
        ]

        if not filtered:
            return {}

        agents = set(r["agent"] for r in filtered)
        scores = {}

        for a in agents:
            agent_records = [r for r in filtered if r["agent"] == a]
            total = len(agent_records)
            correct = sum(1 for r in agent_records if r["correct"])
            accuracy = correct / total if total > 0 else 0

            # Agirlikli skor: dogruluk * guven ortalamasi
            avg_conf = sum(r.get("confidence", 0) for r in agent_records) / total if total > 0 else 0
            weighted = accuracy * avg_conf

            scores[a] = {
                "total_predictions": total,
                "correct": correct,
                "accuracy": round(accuracy * 100, 2),
                "avg_confidence": round(avg_conf, 3),
                "weighted_score": round(weighted, 3),
                "grade": self._grade(accuracy),
            }

        return scores

    def _grade(self, accuracy: float) -> str:
        if accuracy >= 0.80:
            return "A (Mukemmel)"
        elif accuracy >= 0.70:
            return "B (Iyi)"
        elif accuracy >= 0.60:
            return "C (Ortalama)"
        elif accuracy >= 0.50:
            return "D (Zayif)"
        return "F (Kritik)"

    def weak_agents(self, threshold: float = 0.60, days: int = 30) -> List[Dict]:
        """Esik altinda kalan ajanlari listeler."""
        scores = self.calculate_score(days=days)
        return [
            {"agent": a, **data}
            for a, data in scores.items()
            if (data.get("accuracy", 0) / 100) < threshold
        ]

    def report(self, days: int = 30) -> str:
        """Haftalik/aylik rapor metni."""
        scores = self.calculate_score(days=days)
        lines = [
            f"# Ajan Performans Raporu ({days} gun)",
            f"**Tarih:** {datetime.now().strftime('%Y-%m-%d')}\n",
            "| Ajan | Tahmin | Dogru | Dogruluk | Guven | Agirlikli | Not |",
            "|------|--------|-------|----------|-------|-----------|-----|",
        ]
        for a, s in scores.items():
            lines.append(
                f"| {a} | {s['total_predictions']} | {s['correct']} | "
                f"%{s['accuracy']} | {s['avg_confidence']} | "
                f"{s['weighted_score']} | {s['grade']} |"
            )

        weak = self.weak_agents(days=days)
        if weak:
            lines.extend(["\n## Zayif Ajanlar (Uyarili)"])
            for w in weak:
                lines.append(f"- **{w['agent']}**: %{w['accuracy']} dogruluk — {w['grade']}")

        return "\n".join(lines)
