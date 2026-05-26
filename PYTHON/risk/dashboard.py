"""
dashboard.py — CLI tablo ciktisi + HTML rapor
"""
import pandas as pd
from datetime import datetime
from typing import Dict


def cli_table(metrics: Dict) -> str:
    """Terminalde gosterilecek tablo formati."""
    lines = []
    lines.append("=" * 60)
    lines.append("  ANATOLIAX PERFORMANS PANOSU")
    lines.append("=" * 60)
    lines.append(f"{'Metrik':<20} {'Deger':<15} {'Hedef':<15} {'Durum':<6}")
    lines.append("-" * 60)

    simple_metrics = ["sharpe", "sortino", "max_drawdown", "profit_factor", "recovery_factor", "expectancy"]
    for key in simple_metrics:
        if key in metrics and isinstance(metrics[key], dict):
            m = metrics[key]
            val = f"{m['value']:.3f}" if isinstance(m['value'], float) else str(m['value'])
            thr = f"{m['threshold']:.3f}" if isinstance(m['threshold'], float) else str(m['threshold'])
            ok = "✅" if m.get("passed") else "❌"
            lines.append(f"{key.upper():<20} {val:<15} {thr:<15} {ok:<6}")

    lines.append("-" * 60)
    lines.append(f"Monte Carlo 95% CI: [{metrics.get('monte_carlo', {}).get('ci_lower', 0):.3f}, {metrics.get('monte_carlo', {}).get('ci_upper', 0):.3f}]")
    lines.append(f"Walk-Forward Fark:  {metrics.get('walk_forward', {}).get('difference', 0):.3f}")
    lines.append("=" * 60)
    lines.append(f"SONUC: {metrics.get('_summary', 'N/A')} — {metrics.get('_overall', 'N/A')}")
    lines.append("=" * 60)

    return "\n".join(lines)


def html_report(metrics: Dict, trades: pd.DataFrame = None) -> str:
    """HTML formatinda rapor uretir."""
    rows = ""
    simple_metrics = ["sharpe", "sortino", "max_drawdown", "profit_factor", "recovery_factor", "expectancy"]
    for key in simple_metrics:
        if key in metrics and isinstance(metrics[key], dict):
            m = metrics[key]
            val = f"{m['value']:.3f}"
            ok = "✅" if m.get("passed") else "❌"
            rows += f"<tr><td>{key.upper()}</td><td>{val}</td><td>{ok}</td></tr>\n"

    trades_html = ""
    if trades is not None and not trades.empty:
        trades_html = trades.to_html(index=False, classes="table table-striped")

    html = f"""
    <html>
    <head>
        <title>AnatoliaX Raporu</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #333; color: white; }}
            .header {{ background-color: #f4f4f4; padding: 10px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>AnatoliaX Performans Raporu</h1>
            <p>Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            <h2>Sonuc: {metrics.get('_overall', 'N/A')}</h2>
        </div>
        <table>
            <tr><th>Metrik</th><th>Deger</th><th>Durum</th></tr>
            {rows}
        </table>
        <h2>Islem Listesi</h2>
        {trades_html}
    </body>
    </html>
    """
    return html
