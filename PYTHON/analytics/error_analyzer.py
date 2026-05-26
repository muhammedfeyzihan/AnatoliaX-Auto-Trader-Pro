"""
error_analyzer.py — Derinlemesine Hata Analizi (K81-K90 guncelleme)
Her hata icin: zaman, piyasa rejimi, hangi ajan neyi kacirdi, finansal etki, kok neden.
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional


class ErrorAnalyzer:
    """Hata kayitlarini analiz eder ve K81-K90 guncelleme onerileri uretir."""

    LOG_FILE = "anatoliax_errors.jsonl"

    def __init__(self, log_dir: str = None):
        self.log_dir = log_dir or os.getenv("LOG_DIR", ".")
        self.log_path = os.path.join(self.log_dir, self.LOG_FILE)
        self.errors: List[Dict] = []
        self._load()

    def _load(self):
        """Mevcut hata kayitlarini yukler."""
        if os.path.exists(self.log_path):
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.errors.append(json.loads(line))

    def log_error(
        self,
        symbol: str,
        agent: str,
        expected: str,
        actual: str,
        market_regime: str,
        pnl_impact: float = 0.0,
        root_cause_category: str = "",
        description: str = "",
        missed_signals: List[str] = None,
    ) -> Dict:
        """
        Yeni hata kaydi olusturur.

        Args:
            agent: Hangi ajan hata yapti (B, C, D, E, F, G, H)
            expected: Beklenen durum
            actual: Gerceklesen durum
            pnl_impact: Finansal etki (TL cinsinden, negatif = zarar)
            root_cause_category: teknik, haber, risk, makro, manipulasyon, diger
            missed_signals: Kacirilan sinyaller listesi
        """
        record = {
            "id": len(self.errors) + 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol.upper(),
            "agent": agent.upper(),
            "market_regime": market_regime,
            "expected": expected,
            "actual": actual,
            "pnl_impact": pnl_impact,
            "root_cause": root_cause_category,
            "missed_signals": missed_signals or [],
            "description": description,
            "preventive_rule": None,
        }
        self.errors.append(record)
        self._append(record)
        return record

    def _append(self, record: Dict):
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def analyze_patterns(self, agent: str = None, days: int = 30) -> Dict:
        """Hata paternlerini analiz eder."""
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        filtered = [
            e for e in self.errors
            if datetime.fromisoformat(e["timestamp"]) >= cutoff
            and (agent is None or e["agent"] == agent.upper())
        ]

        if not filtered:
            return {"message": "Belirtilen kriterde hata kaydi yok."}

        # Agent bazli dagilim
        agent_dist = {}
        for e in filtered:
            a = e["agent"]
            agent_dist[a] = agent_dist.get(a, 0) + 1

        # Kok neden dagilimi
        cause_dist = {}
        for e in filtered:
            c = e.get("root_cause", "bilinmiyor")
            cause_dist[c] = cause_dist.get(c, 0) + 1

        # Finansal etki
        total_impact = sum(e.get("pnl_impact", 0) for e in filtered)
        avg_impact = total_impact / len(filtered) if filtered else 0

        # En sik tekrar eden hata (3+ tekrar = kural guncelleme)
        error_signatures = {}
        for e in filtered:
            sig = f"{e['agent']}:{e.get('root_cause', '')}:{e.get('expected', '')}"
            error_signatures[sig] = error_signatures.get(sig, 0) + 1

        recurring = {k: v for k, v in error_signatures.items() if v >= 3}

        return {
            "total_errors": len(filtered),
            "total_impact_tl": round(total_impact, 2),
            "avg_impact_tl": round(avg_impact, 2),
            "agent_distribution": agent_dist,
            "root_cause_distribution": cause_dist,
            "recurring_errors": recurring,
            "needs_rule_update": len(recurring) > 0,
        }

    def suggest_rule_update(self) -> List[Dict]:
        """K81-K90 guncelleme onerileri uretir."""
        patterns = self.analyze_patterns()
        suggestions = []

        for sig, count in patterns.get("recurring_errors", {}).items():
            agent, cause, expected = sig.split(":", 2)
            suggestions.append({
                "rule_id": f"K{90 + len(suggestions) + 1}",
                "trigger": f"{agent} ajaninda {cause} nedeniyle {count} kez tekrarlanan hata",
                "action": f"{agent} ajaninin {cause} kontrolu guclendirilmeli. Beklenen: {expected}",
                "affected_agent": agent,
                "frequency": count,
            })

        return suggestions

    def export_markdown(self, output_path: str = None):
        """Hata analizini markdown olarak KURALLAR'a yazar."""
        if output_path is None:
            output_path = os.path.join(
                os.path.dirname(__file__),
                "..", "..", "KURALLAR", "HATA_ANALIZI_VE_GELISIM.md"
            )

        analysis = self.analyze_patterns()
        suggestions = self.suggest_rule_update()

        lines = [
            "# Hata Analizi ve Gelisim Raporu (Otomatik)",
            f"**Tarih:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
            "## Ozet",
            f"- Toplam hata: {analysis.get('total_errors', 0)}",
            f"- Toplam finansal etki: {analysis.get('total_impact_tl', 0):.2f} TL",
            f"- Ortalama etki: {analysis.get('avg_impact_tl', 0):.2f} TL/hata",
            f"- Kural guncelleme gereksinimi: {'EVET' if analysis.get('needs_rule_update') else 'HAYIR'}\n",
            "## Ajan Dagilimi",
        ]
        for agent, count in analysis.get("agent_distribution", {}).items():
            lines.append(f"- **Ajan {agent}:** {count} hata")

        lines.extend(["\n## Kok Neden Dagilimi"])
        for cause, count in analysis.get("root_cause_distribution", {}).items():
            lines.append(f"- **{cause}:** {count} hata")

        if suggestions:
            lines.extend(["\n## Onerilen Kural Guncellemeleri"])
            for s in suggestions:
                lines.extend([
                    f"\n### {s['rule_id']}",
                    f"- **Tetikleyici:** {s['trigger']}",
                    f"- **Eylem:** {s['action']}",
                    f"- **Etkilenen Ajan:** {s['affected_agent']}",
                    f"- **Tekrar Sayisi:** {s['frequency']}",
                ])

        with open(output_path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n\n")
