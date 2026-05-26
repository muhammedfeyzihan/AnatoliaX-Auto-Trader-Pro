"""
chart_generator.py — AutoTrader entegre edilmis Bokeh backtest grafikleri
Fiyat + EMA + alim/satim noktalari + equity curve + drawdown.

Kullanim:
    from backtest.chart_generator import BacktestChartGenerator
    chart = BacktestChartGenerator(df, trades_df, equity_df)
    chart.save_html("reports/backtest_THYAO.html")
"""
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

import pandas as pd
import numpy as np
from datetime import datetime


class BacktestChartGenerator:
    """
    Backtest sonuclarini interaktif HTML grafiğe çevirir.
    Bokeh kuruluysa Bokeh, yoksa matplotlib ile fallback.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        trades_df: pd.DataFrame,
        equity_df: pd.DataFrame,
        title: str = "Backtest Raporu",
    ):
        self.df = df.copy()
        self.trades = trades_df.copy() if not trades_df.empty else pd.DataFrame()
        self.equity = equity_df.copy() if not equity_df.empty else pd.DataFrame()
        self.title = title

    def _calculate_drawdown(self) -> pd.Series:
        """Equity curve'den drawdown hesapla."""
        if self.equity.empty or "equity" not in self.equity.columns:
            return pd.Series(dtype=float)
        eq = self.equity["equity"]
        peak = eq.cummax()
        dd = (eq - peak) / peak * 100
        return dd

    def _get_bokeh(self):
        try:
            import bokeh.plotting as bp
            from bokeh.layouts import column
            from bokeh.models import HoverTool, CrosshairTool
            return bp, column, HoverTool, CrosshairTool
        except Exception:
            return None, None, None, None

    def create_charts(self) -> str:
        """
        HTML icerigi uret.
        Returns: HTML string
        """
        bp, column, HoverTool, CrosshairTool = self._get_bokeh()
        if bp is None:
            return self._create_matplotlib_fallback()
        return self._create_bokeh_charts(bp, column, HoverTool, CrosshairTool)

    def _create_bokeh_charts(self, bp, column, HoverTool, CrosshairTool):
        import bokeh.plotting as bp

        # Fiyat grafiği
        p1 = bp.figure(
            title=self.title,
            x_axis_type="datetime",
            width=1200,
            height=400,
            tools="pan,wheel_zoom,box_zoom,reset,save",
        )
        p1.line(self.df.index, self.df["close"], line_width=1.5, color="black", legend_label="Close")

        if "EMA9" in self.df.columns:
            p1.line(self.df.index, self.df["EMA9"], line_width=1, color="blue", alpha=0.6, legend_label="EMA9")
        if "EMA21" in self.df.columns:
            p1.line(self.df.index, self.df["EMA21"], line_width=1, color="orange", alpha=0.6, legend_label="EMA21")

        # Alim/Satim noktalari
        if not self.trades.empty:
            for _, t in self.trades.iterrows():
                try:
                    entry_idx = int(t["entry_idx"])
                    exit_idx = int(t["exit_idx"])
                    entry_price = float(t["entry_price"])
                    exit_price = float(t["exit_price"])
                    reason = str(t["reason"])
                    if entry_idx < len(self.df) and exit_idx < len(self.df):
                        entry_time = self.df.index[entry_idx]
                        exit_time = self.df.index[exit_idx]
                        color = "green" if reason.startswith("TP") else "red" if reason in ["SL", "TRAILING_STOP", "TIME_EXIT"] else "gray"
                        p1.circle(entry_time, entry_price, size=8, color="blue", legend_label="Entry")
                        p1.triangle(exit_time, exit_price, size=8, color=color, legend_label=f"Exit ({reason})")
                except Exception:
                    pass

        # Equity curve
        p2 = bp.figure(
            x_axis_type="datetime",
            width=1200,
            height=250,
            x_range=p1.x_range,
            tools="pan,wheel_zoom,box_zoom,reset,save",
        )
        if not self.equity.empty and "equity" in self.equity.columns:
            p2.line(self.equity.index, self.equity["equity"], line_width=2, color="green", legend_label="Equity")

        # Drawdown
        p3 = bp.figure(
            x_axis_type="datetime",
            width=1200,
            height=150,
            x_range=p1.x_range,
            tools="pan,wheel_zoom,box_zoom,reset,save",
        )
        dd = self._calculate_drawdown()
        if not dd.empty:
            p3.line(dd.index, dd, line_width=1, color="red", legend_label="Drawdown %")
            p3.yaxis.axis_label = "Drawdown %"

        layout = column(p1, p2, p3)
        from bokeh.embed import file_html
        from bokeh.resources import CDN
        html = file_html(layout, CDN, self.title)
        return html

    def _create_matplotlib_fallback(self):
        """Bokeh yoksa basit HTML table fallback."""
        # Trade ozeti tablosu
        trade_rows = ""
        if not self.trades.empty:
            for _, t in self.trades.iterrows():
                trade_rows += f"""
                <tr>
                    <td>{t.get('entry_price', '')}</td>
                    <td>{t.get('exit_price', '')}</td>
                    <td>{round(t.get('net_pnl', 0), 2)}</td>
                    <td>{t.get('reason', '')}</td>
                </tr>
                """
        else:
            trade_rows = "<tr><td colspan='4'>Islem yok</td></tr>"

        # Equity summary
        eq_start = self.equity["equity"].iloc[0] if not self.equity.empty and "equity" in self.equity.columns else 0
        eq_end = self.equity["equity"].iloc[-1] if not self.equity.empty and "equity" in self.equity.columns else 0
        dd = self._calculate_drawdown()
        max_dd = round(dd.min(), 2) if not dd.empty else 0.0

        html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>{self.title}</title>
        <style>
            body {{ font-family:sans-serif; padding:20px; }}
            table {{ border-collapse:collapse; width:100%; margin-top:10px; }}
            th, td {{ border:1px solid #ccc; padding:6px; text-align:left; }}
            th {{ background:#f0f0f0; }}
            .summary {{ display:flex; gap:20px; margin-bottom:15px; }}
            .box {{ border:1px solid #ddd; padding:10px; border-radius:4px; min-width:120px; }}
        </style>
        </head>
        <body>
            <h2>{self.title}</h2>
            <p>Bokeh ve matplotlib kurulu degil. Basit HTML ozet.</p>
            <div class="summary">
                <div class="box"><b>Baslangic:</b><br>{eq_start:,.0f}</div>
                <div class="box"><b>Bitis:</b><br>{eq_end:,.0f}</div>
                <div class="box"><b>Getiri:</b><br>{round((eq_end-eq_start)/eq_start*100,1) if eq_start else 0}%</div>
                <div class="box"><b>Max DD:</b><br>{max_dd}%</div>
            </div>
            <table>
                <tr><th>Entry</th><th>Exit</th><th>PnL</th><th>Reason</th></tr>
                {trade_rows}
            </table>
        </body>
        </html>
        """
        return html

    def save_html(self, output_path: str | Path) -> Path:
        """
        Grafiği HTML dosyasına kaydet.
        Returns: kaydedilen dosya yolu
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        html = self.create_charts()
        path.write_text(html, encoding="utf-8")
        return path


if __name__ == "__main__":
    # Demo
    import numpy as np
    rows = 200
    idx = pd.date_range("2026-01-01", periods=rows, freq="D")
    df = pd.DataFrame({
        "open": np.cumsum(np.random.randn(rows)) + 100,
        "high": np.cumsum(np.random.randn(rows)) + 102,
        "low": np.cumsum(np.random.randn(rows)) + 98,
        "close": np.cumsum(np.random.randn(rows)) + 100,
        "volume": np.ones(rows) * 1_000_000,
        "EMA9": np.cumsum(np.random.randn(rows)) + 100,
        "EMA21": np.cumsum(np.random.randn(rows)) + 100,
    }, index=idx)

    trades = pd.DataFrame({
        "entry_idx": [10, 50, 100],
        "exit_idx": [20, 65, 150],
        "entry_price": [100.0, 105.0, 110.0],
        "exit_price": [102.0, 104.0, 108.0],
        "reason": ["TP1", "SL", "TP2"],
        "net_pnl": [200.0, -150.0, 300.0],
    })

    equity = pd.DataFrame({"equity": np.cumsum(np.random.randn(rows) * 100) + 100_000}, index=idx)

    gen = BacktestChartGenerator(df, trades, equity, title="Demo Backtest")
    out = gen.save_html("reports/backtest_demo.html")
    print(f"Kaydedildi: {out}")
