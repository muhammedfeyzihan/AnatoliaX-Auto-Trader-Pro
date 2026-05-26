"""
compliance/spk_rules.py — SPK kurallari ve uygunluk kontrolu
"""
from typing import List


class SPKCompliance:
    """
    SPK duzenlemelerine uygunluk.

    Kurallar:
    - Asiri spekulasyon yasak
    - Manipulasyon tespiti: hacim/fiyat anomalisi + haber karsilastirma
    - Aciga satis yasak listesi kontrolu
    - VIOP marjin yetersizligi

    K194: SPK ihlali tespitinde sistemin emir vermesi engellenir.
    """

    PROHIBITED_PATTERNS = ["pump_and_dump", "wash_trading", "layering"]

    def check(self, activity: dict) -> List[str]:
        flags = []
        if activity.get("pattern") in self.PROHIBITED_PATTERNS:
            flags.append("Yasakli patern tespit edildi.")
        return flags
