"""
debate_panel.py — Yapilandirilmis Bull/Bear tartisma paneli.
tradingagents'tan entegre edilmistir.

Kullanim:
    from agents.debate_panel import DebatePanel
    panel = DebatePanel(symbol="THYAO")
    result = panel.debate(
        bull_args={"teknik": "AL", "haber": "pozitif", "ps": 85},
        bear_args={"teknik": "SAT", "haber": "negatif", "ps": 35},
    )
    # result: {"consensus_score": 62, "risk_etiketi": "UYGUN", "tavsiye": "AL"}
"""
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

from typing import Optional


class DebatePanel:
    """
    Her hisse icin Bull (iyimser) ve Bear (kotumser) ajanlar tartisir.
    Format: Bull iddia -> Bear curutme -> Bull yanit -> Karar (oylama).

    Cikti:
        consensus_score: 0-100 (50 uzeri = Bull agirlikli)
        risk_etiketi: UYGUN / SINIRLI / RED
        tavsiye: AL / IZLE / PASS
        gerekce: str
    """

    def __init__(self, symbol: str, verbose: bool = False):
        self.symbol = symbol
        self.verbose = verbose
        self._transcript: list[dict] = []
        # Strateji Ajanı — Kimi/Bulut entegrasyonu
        from ai.cloud_client import StrategyAgentAI
        self.ai_strategy = StrategyAgentAI()

    def debate(
        self,
        bull_args: dict,
        bear_args: dict,
    ) -> dict:
        """
        Tartismayi yurut.

        Parametreler:
            bull_args: {"teknik": str, "haber": str, "ps": int, "risk": str, "makro": str}
            bear_args: {"teknik": str, "haber": str, "ps": int, "risk": str, "makro": str}

        Donus: {"consensus_score": int, "risk_etiketi": str, "tavsiye": str, "gerekce": str, "transcript": list}
        """
        self._transcript = []

        # 1. Bull iddia
        bull_claim = self._bull_claim(bull_args)
        self._transcript.append({"side": "BULL", "type": "claim", "text": bull_claim})

        # 2. Bear curutme
        bear_rebuttal = self._bear_rebuttal(bull_args, bear_args)
        self._transcript.append({"side": "BEAR", "type": "rebuttal", "text": bear_rebuttal})

        # 3. Bull yanit
        bull_response = self._bull_response(bull_args, bear_args)
        self._transcript.append({"side": "BULL", "type": "response", "text": bull_response})

        # 4. Karar (matematiksel oylama)
        result = self._vote(bull_args, bear_args)
        self._transcript.append({"side": "JURI", "type": "vote", "text": result["gerekce"]})

        # Strateji Ajanı — Gemma/Ollama nihai karar gerekcesi
        ai_rationale = self.ai_strategy.decision_rationale(
            self.symbol,
            context={
                "signal_score": bull_args.get("ps", 0),
                "risk_label": result.get("risk_etiketi", "UNKNOWN"),
                "regime": bull_args.get("makro", "UNKNOWN"),
                "kelly": bull_args.get("kelly", 0.0),
                "r_r": bull_args.get("r_r", 0.0),
            }
        )
        result["ai_rationale"] = ai_rationale

        if self.verbose:
            for line in self._transcript:
                print(f"[{line['side']}] {line['type']}: {line['text']}")

        result["transcript"] = self._transcript
        return result

    @staticmethod
    def _bull_claim(args: dict) -> str:
        teknik = args.get("teknik", "N/A")
        ps = args.get("ps", 0)
        return f"Teknik: {teknik} | PS skoru: {ps} | Yukari momentum guclu."

    @staticmethod
    def _bear_rebuttal(bull: dict, bear: dict) -> str:
        bear_ps = bear.get("ps", 0)
        bull_ps = bull.get("ps", 0)
        if bear_ps < bull_ps:
            return f"PS skoru {bear_ps} < {bull_ps}, ancak haber akisi {bear.get('haber', 'belirsiz')}."
        return f"PS skoru {bear_ps} daha dusuk. Haber: {bear.get('haber', 'belirsiz')}. Beklemede kalinmalı."

    @staticmethod
    def _bull_response(bull: dict, bear: dict) -> str:
        if bull.get("makro", "") == "BOGA" and bear.get("makro", "") != "BOGA":
            return "Makro rejim BOGA. Asimetrik risk/odul lehimize."
        return f"Risk etiketi {bull.get('risk', 'UYGUN')}. Pozisyon acilabilir."

    @staticmethod
    def _vote(bull: dict, bear: dict) -> dict:
        """
        Tartisma sonucu oy hesaplama.
        Her kriter 0-25 puan, toplam 0-100.
        """
        bull_ps = bull.get("ps", 50)
        bear_ps = bear.get("ps", 50)
        teknik_delta = (bull_ps - bear_ps) / 2  # -25 .. +25

        haber_score = 0
        if bull.get("haber", "") == "pozitif":
            haber_score = 15
        elif bull.get("haber", "") == "notr":
            haber_score = 5
        if bear.get("haber", "") == "negatif":
            haber_score -= 10

        risk_score = 0
        if bull.get("risk", "UYGUN") == "UYGUN":
            risk_score = 10
        if bear.get("risk", "UYGUN") == "RED":
            risk_score -= 10

        makro_score = 0
        if bull.get("makro", "") == "BOGA":
            makro_score = 10
        elif bull.get("makro", "") == "AYI":
            makro_score = -10

        raw_score = 50 + teknik_delta + haber_score + risk_score + makro_score
        consensus = int(max(0, min(100, raw_score)))

        if consensus >= 70:
            tavsiye = "AL"
            risk_etiketi = "UYGUN"
        elif consensus >= 45:
            tavsiye = "IZLE"
            risk_etiketi = "SINIRLI"
        else:
            tavsiye = "PASS"
            risk_etiketi = "RED"

        gerekce = (
            f"Consensus: {consensus}/100 | "
            f"Teknik delta: {teknik_delta:+.1f}, Haber: {haber_score:+d}, "
            f"Risk: {risk_score:+d}, Makro: {makro_score:+d}. "
            f"Tavsiye: {tavsiye}."
        )

        return {
            "consensus_score": consensus,
            "risk_etiketi": risk_etiketi,
            "tavsiye": tavsiye,
            "gerekce": gerekce,
        }

    @staticmethod
    def quick_debate(symbol: str, bull: dict, bear: dict) -> dict:
        """
        Tek satirda debate sonucu al.
        """
        return DebatePanel(symbol=symbol).debate(bull_args=bull, bear_args=bear)


if __name__ == "__main__":
    panel = DebatePanel(symbol="THYAO", verbose=True)
    result = panel.debate(
        bull_args={"teknik": "AL", "haber": "pozitif", "ps": 85, "risk": "UYGUN", "makro": "BOGA"},
        bear_args={"teknik": "SAT", "haber": "notr", "ps": 35, "risk": "UYGUN", "makro": "YAN"},
    )
    print("\n--- SONUC ---")
    print(result["gerekce"])
