"""
anatoliax_jobs.py — AnatoliaX standart zamanlanmis gorevleri.

Kullanim:
    from scheduler.anatoliax_jobs import register_all_jobs
    sched = TaskScheduler()
    register_all_jobs(sched)
    sched.start()
"""
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

from scheduler.task_scheduler import TaskScheduler


class AnatoliaXJobs:
    """
    AnatoliaX saat kurallarina gore tanimlanmis gorevler.
    """

    def __init__(self, scheduler: TaskScheduler):
        self.sched = scheduler

    def register_all(self):
        """Tum standart gorevleri kaydet."""
        self._register_signal_scan()
        self._register_risk_check()
        self._register_morning_report()
        self._register_opening_report()
        self._register_midday_report()
        self._register_evening_report()
        self._register_health_check()
        self._register_subscription_check()
        self._register_rule_evolution()

    def _register_signal_scan(self):
        def _scan():
            print("[SCHEDULER] Sinyal taramasi basladi")
            try:
                from paper_trading.signal_engine import SignalEngine
                engine = SignalEngine(paper_trading=False)
                # Demo: BIST 30 hisseleri (gercek uygulamada dinamik liste)
                symbols = ["THYAO", "GARAN", "ASELS", "TUPRS", "KCHOL"]
                results = engine.run_scan(symbols)
                print(f"[SCHEDULER] Tarama tamamlandi: {len(results)} sonuc")
            except Exception as e:
                print(f"[SCHEDULER] Sinyal tarama hatasi: {e}")

        self.sched.add_interval_job(_scan, minutes=15, job_id="signal_scan_15m")

    def _register_risk_check(self):
        def _risk():
            print("[SCHEDULER] Risk kontrolu basladi")
            try:
                from risk.kill_switch import KillSwitch
                ks = KillSwitch(max_drawdown=20.0, daily_loss_limit=3.0)
                if not ks.is_trading_allowed():
                    print("[SCHEDULER] KILL SWITCH AKTIF - Islem yapilamaz")
                else:
                    print("[SCHEDULER] Risk kontrolu OK")
            except Exception as e:
                print(f"[SCHEDULER] Risk kontrol hatasi: {e}")

        self.sched.add_interval_job(_risk, minutes=60, job_id="risk_check_1h")

    def _register_morning_report(self):
        def _morning():
            print("[SCHEDULER] Sabah raporu gonderiliyor (08:30)")
            try:
                from telegram.reporter import send_report
                send_report(report_type="morning")
            except Exception as e:
                print(f"[SCHEDULER] Sabah raporu hatasi: {e}")

        self.sched.add_daily_job(_morning, hour=8, minute=30, job_id="morning_report")

    def _register_opening_report(self):
        def _opening():
            print("[SCHEDULER] Acilis raporu gonderiliyor (09:30)")
            try:
                from telegram.reporter import send_report
                send_report(report_type="opening")
            except Exception as e:
                print(f"[SCHEDULER] Acilis raporu hatasi: {e}")

        self.sched.add_daily_job(_opening, hour=9, minute=30, job_id="opening_report")

    def _register_midday_report(self):
        def _midday():
            print("[SCHEDULER] Ogle raporu gonderiliyor (14:00)")
            try:
                from telegram.reporter import send_report
                send_report(report_type="midday")
            except Exception as e:
                print(f"[SCHEDULER] Ogle raporu hatasi: {e}")

        self.sched.add_daily_job(_midday, hour=14, minute=0, job_id="midday_report")

    def _register_evening_report(self):
        def _evening():
            print("[SCHEDULER] Kapanis raporu gonderiliyor (17:30)")
            try:
                from telegram.reporter import send_report
                send_report(report_type="evening")
            except Exception as e:
                print(f"[SCHEDULER] Kapanis raporu hatasi: {e}")

        self.sched.add_daily_job(_evening, hour=17, minute=30, job_id="evening_report")

    def _register_health_check(self):
        def _health():
            print("[SCHEDULER] Saglik kontrolu (07:30)")
            try:
                from monitor.health_check import HealthCheck
                hc = HealthCheck()
                result = hc.run()
                if result.get("status") != "OK":
                    print(f"[SCHEDULER] WARN: {result}")
            except Exception as e:
                print(f"[SCHEDULER] Health check hatasi: {e}")

        self.sched.add_daily_job(_health, hour=7, minute=30, job_id="health_check")

    def _register_subscription_check(self):
        def _subs():
            print("[SCHEDULER] Abonelik kontrolu")
            try:
                from telegram.subscription_manager import SubscriptionManager
                sm = SubscriptionManager()
                # Demo: THYAO fiyat kontrolu
                # Gercek uygulamada tum abonelikler taranir
                triggers = sm.check_subscriptions("THYAO", current_price=0.0)
                for t in triggers:
                    print(f"[SCHEDULER] ALARM: {t['message']}")
            except Exception as e:
                print(f"[SCHEDULER] Abonelik kontrol hatasi: {e}")

        self.sched.add_interval_job(_subs, minutes=5, job_id="subscription_check_5m")

    def _register_rule_evolution(self):
        def _evolve():
            print("[SCHEDULER] Kural evrimi basladi (16:30)")
            try:
                from agents.rule_evolution import RuleEvolution
                evo = RuleEvolution()
                suggestions = evo.analyze_and_evolve()
                if suggestions and suggestions[0].get("rule") != "NOP":
                    print(f"[SCHEDULER] Kural evrim onerileri: {len(suggestions)} adet")
                    for s in suggestions:
                        print(f"  - {s['rule']}: {s.get('old_value')} -> {s.get('new_value')} | {s['reason']}")
                else:
                    print("[SCHEDULER] Kural evrimi: Yetersiz veri veya degisiklik yok")
            except Exception as e:
                print(f"[SCHEDULER] Kural evrim hatasi: {e}")

        self.sched.add_daily_job(_evolve, hour=16, minute=30, job_id="rule_evolution_1630")


def register_all_jobs(scheduler: TaskScheduler):
    jobs = AnatoliaXJobs(scheduler)
    jobs.register_all()


if __name__ == "__main__":
    from scheduler.task_scheduler import TaskScheduler
    sched = TaskScheduler()
    register_all_jobs(sched)
    print("Kayitli gorevler:", [j["id"] for j in sched.list_jobs()])
