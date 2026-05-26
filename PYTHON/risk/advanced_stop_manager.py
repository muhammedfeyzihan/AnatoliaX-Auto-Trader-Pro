"""
advanced_stop_manager.py — AutoTrader entegre edilmis gelismis stop yonetimi.

Kullanim:
    from risk.advanced_stop_manager import TrailingStop, ChandelierExit
    ts = TrailingStop(entry=100.0, atr=2.5, multiplier=2.0, side="BUY")
    sl = ts.update(new_price=105.0)
"""
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

import numpy as np
import pandas as pd
from typing import Optional, Literal


class TrailingStop:
    """
    ATR bazli veya fiyat bazli trailing stop.

    Parametreler:
        entry: Giris fiyati
        atr: Mevcut ATR degeri (yoksa initial_stop kullanilir)
        multiplier: ATR carpani (varsayilan 2.0)
        side: "BUY" veya "SELL"
        initial_stop: Baslangic SL (atr yoksa zorunlu)
        step_type: "atr" veya "price" (price = her %1 kazanc SL'yi %0.5 ceker)
    """

    def __init__(
        self,
        entry: float,
        atr: Optional[float] = None,
        multiplier: float = 2.0,
        side: Literal["BUY", "SELL"] = "BUY",
        initial_stop: Optional[float] = None,
        step_type: Literal["atr", "price"] = "atr",
    ):
        self.entry = float(entry)
        self.side = side
        self.step_type = step_type
        self.multiplier = multiplier
        self.atr = atr

        if side == "BUY":
            if initial_stop is not None:
                self.current_sl = float(initial_stop)
            elif atr is not None:
                self.current_sl = entry - (atr * multiplier)
            else:
                raise ValueError("BUY icin 'atr' veya 'initial_stop' gerekli")
        else:  # SELL
            if initial_stop is not None:
                self.current_sl = float(initial_stop)
            elif atr is not None:
                self.current_sl = entry + (atr * multiplier)
            else:
                raise ValueError("SELL icin 'atr' veya 'initial_stop' gerekli")

        self.highest_price = entry if side == "BUY" else entry
        self.lowest_price = entry if side == "SELL" else entry
        self.triggered = False
        self.history: list[tuple[float, float]] = [(entry, self.current_sl)]

    def update(self, new_price: float) -> float:
        """
        Yeni fiyatla SL'yi guncelle. Tetiklendi ise True dondur.
        Donus: mevcut SL seviyesi
        """
        if self.triggered:
            return self.current_sl

        new_price = float(new_price)

        if self.side == "BUY":
            if new_price > self.highest_price:
                self.highest_price = new_price
                if self.step_type == "atr" and self.atr:
                    new_sl = new_price - (self.atr * self.multiplier)
                    if new_sl > self.current_sl:
                        self.current_sl = new_sl
                elif self.step_type == "price":
                    gain_pct = (new_price - self.entry) / self.entry
                    step = gain_pct * 0.5 * self.entry
                    new_sl = self.entry + step
                    if new_sl > self.current_sl:
                        self.current_sl = new_sl

            if new_price <= self.current_sl:
                self.triggered = True

        else:  # SELL
            if new_price < self.lowest_price:
                self.lowest_price = new_price
                if self.step_type == "atr" and self.atr:
                    new_sl = new_price + (self.atr * self.multiplier)
                    if new_sl < self.current_sl:
                        self.current_sl = new_sl
                elif self.step_type == "price":
                    gain_pct = (self.entry - new_price) / self.entry
                    step = gain_pct * 0.5 * self.entry
                    new_sl = self.entry - step
                    if new_sl < self.current_sl:
                        self.current_sl = new_sl

            if new_price >= self.current_sl:
                self.triggered = True

        self.history.append((new_price, self.current_sl))
        return round(self.current_sl, 4)

    def is_triggered(self) -> bool:
        return self.triggered

    def summary(self) -> dict:
        return {
            "entry": self.entry,
            "side": self.side,
            "current_sl": round(self.current_sl, 4),
            "highest_price": round(self.highest_price, 4),
            "lowest_price": round(self.lowest_price, 4),
            "triggered": self.triggered,
            "history_count": len(self.history),
        }


class ChandelierExit:
    """
    Chandelier Exit: En yuksek high - 3xATR (BUY) veya
    En dusuk low + 3xATR (SELL).

    Kullanim:
        ce = ChandelierExit(df_high, df_low, df_close, period=22, atr_period=22, multiplier=3.0)
        sl_series = ce.calculate()
    """

    def __init__(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 22,
        atr_period: int = 22,
        multiplier: float = 3.0,
    ):
        self.high = high
        self.low = low
        self.close = close
        self.period = period
        self.atr_period = atr_period
        self.multiplier = multiplier

    @staticmethod
    def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=1).mean()

    def calculate(self) -> pd.DataFrame:
        """
        Chandelier Exit cizgilerini hesapla.

        Donus: DataFrame [long_stop, short_stop, direction]
            direction: 1 = long aktif, -1 = short aktif
        """
        atr = self._atr(self.high, self.low, self.close, self.atr_period)
        highest_high = self.high.rolling(window=self.period, min_periods=1).max()
        lowest_low = self.low.rolling(window=self.period, min_periods=1).min()

        long_stop = highest_high - (atr * self.multiplier)
        short_stop = lowest_low + (atr * self.multiplier)

        direction = pd.Series(index=self.close.index, dtype=int)
        direction.iloc[0] = 1

        for i in range(1, len(self.close)):
            if self.close.iloc[i] > short_stop.iloc[i - 1]:
                direction.iloc[i] = 1
            elif self.close.iloc[i] < long_stop.iloc[i - 1]:
                direction.iloc[i] = -1
            else:
                direction.iloc[i] = direction.iloc[i - 1]

        return pd.DataFrame(
            {
                "long_stop": long_stop.round(4),
                "short_stop": short_stop.round(4),
                "direction": direction,
            },
            index=self.close.index,
        )


class ParabolicSARStop:
    """
    Parabolic SAR bazli stop.

    Parametreler:
        af_step: Acceleration Factor baslangic (varsayilan 0.02)
        af_max: Max Acceleration Factor (varsayilan 0.20)
    """

    def __init__(
        self,
        high: pd.Series,
        low: pd.Series,
        af_step: float = 0.02,
        af_max: float = 0.20,
    ):
        self.high = high
        self.low = low
        self.af_step = af_step
        self.af_max = af_max

    def calculate(self) -> pd.DataFrame:
        """
        Parabolic SAR serisini hesapla.

        Donus: DataFrame [psar, trend]
            trend: 1 = yukselis, -1 = dusus
        """
        n = len(self.high)
        psar = pd.Series(index=self.high.index, dtype=float)
        trend = pd.Series(index=self.high.index, dtype=int)

        # Baslangic
        psar.iloc[0] = self.low.iloc[0]
        trend.iloc[0] = 1
        af = self.af_step
        ep = self.high.iloc[0]

        for i in range(1, n):
            if trend.iloc[i - 1] == 1:
                psar.iloc[i] = psar.iloc[i - 1] + af * (ep - psar.iloc[i - 1])
                if self.low.iloc[i] < psar.iloc[i]:
                    trend.iloc[i] = -1
                    psar.iloc[i] = ep
                    af = self.af_step
                    ep = self.low.iloc[i]
                else:
                    trend.iloc[i] = 1
                    if self.high.iloc[i] > ep:
                        ep = self.high.iloc[i]
                        af = min(af + self.af_step, self.af_max)
            else:
                psar.iloc[i] = psar.iloc[i - 1] + af * (ep - psar.iloc[i - 1])
                if self.high.iloc[i] > psar.iloc[i]:
                    trend.iloc[i] = 1
                    psar.iloc[i] = ep
                    af = self.af_step
                    ep = self.high.iloc[i]
                else:
                    trend.iloc[i] = -1
                    if self.low.iloc[i] < ep:
                        ep = self.low.iloc[i]
                        af = min(af + self.af_step, self.af_max)

        return pd.DataFrame({"psar": psar.round(4), "trend": trend}, index=self.high.index)


class TimeBasedExit:
    """
    Zaman bazli otomatik kapanis.

    Parametreler:
        max_bars: Maksimum bar sayisi (ornegin 5 gunluk = 5 gun * 8 saat ~= 40 bar 15dk)
        max_days: Takvim gunu limiti (alternatif)
    """

    def __init__(
        self,
        entry_time: pd.Timestamp,
        max_bars: Optional[int] = None,
        max_days: Optional[int] = None,
    ):
        self.entry_time = entry_time
        self.max_bars = max_bars
        self.max_days = max_days
        self.bar_count = 0

    def update(self, current_time: pd.Timestamp) -> bool:
        """
        Zaman asimi kontrolu.

        Donus: True = kapat (time exit tetiklendi)
        """
        if self.max_days is not None:
            elapsed_days = (current_time - self.entry_time).total_seconds() / 86400.0
            if elapsed_days >= self.max_days:
                return True

        if self.max_bars is not None:
            self.bar_count += 1
            if self.bar_count >= self.max_bars:
                return True

        return False

    def remaining_bars(self) -> Optional[int]:
        if self.max_bars is None:
            return None
        return max(0, self.max_bars - self.bar_count)

    def remaining_days(self, current_time: pd.Timestamp) -> Optional[float]:
        if self.max_days is None:
            return None
        elapsed = (current_time - self.entry_time).total_seconds() / 86400.0
        return max(0.0, self.max_days - elapsed)


class VolatilityBasedStop:
    """
    Volatiliteye gore SL mesafesini dinamik olarak ayarlar.

    Parametreler:
        base_sl_pct: Temel SL yuzdesi (ornegin %2)
        atr: Mevcut ATR
        atr_ema: ATR'in EMA'si (ortalama volatilite)
        expand_factor: Volatilite yuksekse genisletme carpani
        contract_factor: Volatilite dusukse daraltma carpani
    """

    def __init__(
        self,
        entry: float,
        base_sl_pct: float = 2.0,
        atr: Optional[float] = None,
        atr_ema: Optional[float] = None,
        expand_factor: float = 1.5,
        contract_factor: float = 0.75,
        side: Literal["BUY", "SELL"] = "BUY",
    ):
        self.entry = entry
        self.base_sl_pct = base_sl_pct
        self.atr = atr
        self.atr_ema = atr_ema
        self.expand_factor = expand_factor
        self.contract_factor = contract_factor
        self.side = side

    def calculate(self) -> float:
        """
        Uygun SL seviyesini hesapla.

        Donus: SL fiyati
        """
        if self.atr and self.atr_ema and self.atr_ema > 0:
            ratio = self.atr / self.atr_ema
            if ratio > 1.2:
                adjusted_pct = self.base_sl_pct * self.expand_factor
            elif ratio < 0.8:
                adjusted_pct = self.base_sl_pct * self.contract_factor
            else:
                adjusted_pct = self.base_sl_pct
        else:
            adjusted_pct = self.base_sl_pct

        if self.side == "BUY":
            sl = self.entry * (1 - adjusted_pct / 100.0)
        else:
            sl = self.entry * (1 + adjusted_pct / 100.0)

        return round(sl, 4)

    def adjust_for_gap(self, gap_pct: float) -> float:
        """
        Gap acilisi varsa SL'yi genislet.

        Donus: ayarlanmis SL
        """
        adjusted_pct = self.base_sl_pct + abs(gap_pct)
        if self.side == "BUY":
            sl = self.entry * (1 - adjusted_pct / 100.0)
        else:
            sl = self.entry * (1 + adjusted_pct / 100.0)
        return round(sl, 4)


class CompositeStopManager:
    """
    Tum gelismis stop turlerini tek yerden yoneten yonetici.
    Entegrasyon noktasi: PaperBroker ve ExecutionEngine.
    """

    def __init__(self):
        self.stops: dict[str, dict] = {}

    def add_trailing_stop(
        self,
        order_id: str,
        entry: float,
        atr: Optional[float] = None,
        multiplier: float = 2.0,
        side: Literal["BUY", "SELL"] = "BUY",
        initial_stop: Optional[float] = None,
        step_type: Literal["atr", "price"] = "atr",
    ) -> TrailingStop:
        ts = TrailingStop(
            entry=entry,
            atr=atr,
            multiplier=multiplier,
            side=side,
            initial_stop=initial_stop,
            step_type=step_type,
        )
        self.stops[order_id] = {"type": "trailing", "obj": ts}
        return ts

    def add_time_exit(
        self,
        order_id: str,
        entry_time: pd.Timestamp,
        max_bars: Optional[int] = None,
        max_days: Optional[int] = None,
    ) -> TimeBasedExit:
        te = TimeBasedExit(entry_time=entry_time, max_bars=max_bars, max_days=max_days)
        self.stops[order_id] = {"type": "time", "obj": te}
        return te

    def update(self, order_id: str, new_price: float, current_time: Optional[pd.Timestamp] = None) -> dict:
        """
        Bir pozisyonun stop durumunu guncelle.

        Donus: {"order_id": str, "action": "HOLD"|"CLOSE", "reason": str, "sl": float|None}
        """
        if order_id not in self.stops:
            return {"order_id": order_id, "action": "HOLD", "reason": "No stop registered", "sl": None}

        stop = self.stops[order_id]
        obj = stop["obj"]

        if stop["type"] == "trailing":
            sl = obj.update(new_price)
            if obj.is_triggered():
                return {"order_id": order_id, "action": "CLOSE", "reason": "Trailing stop triggered", "sl": sl}
            return {"order_id": order_id, "action": "HOLD", "reason": "Trailing active", "sl": sl}

        if stop["type"] == "time":
            if current_time is None:
                return {"order_id": order_id, "action": "HOLD", "reason": "Time exit needs current_time", "sl": None}
            triggered = obj.update(current_time)
            if triggered:
                return {"order_id": order_id, "action": "CLOSE", "reason": "Time-based exit triggered", "sl": None}
            return {"order_id": order_id, "action": "HOLD", "reason": "Time exit active", "sl": None}

        return {"order_id": order_id, "action": "HOLD", "reason": "Unknown stop type", "sl": None}

    def remove(self, order_id: str) -> bool:
        if order_id in self.stops:
            del self.stops[order_id]
            return True
        return False

    def list_active(self) -> list[str]:
        return list(self.stops.keys())


if __name__ == "__main__":
    # Demo: TrailingStop
    ts = TrailingStop(entry=100.0, atr=2.5, multiplier=2.0, side="BUY", step_type="atr")
    for price in [100.0, 102.0, 105.0, 104.0, 103.0, 96.0]:
        sl = ts.update(price)
        print(f"Price: {price} -> SL: {sl}, Triggered: {ts.is_triggered()}")

    print("\nSummary:", ts.summary())

    # Demo: TimeBasedExit
    te = TimeBasedExit(entry_time=pd.Timestamp("2026-05-20 09:30"), max_days=5)
    print("\nTime exit triggered?", te.update(pd.Timestamp("2026-05-25 10:00")))
