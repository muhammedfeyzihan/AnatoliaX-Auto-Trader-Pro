"""
run_scheduler.py — AnatoliaX Zamanlayici Runner

Kullanim:
    python PYTHON/scheduler/run_scheduler.py
    # veya arka planda:
    # Windows: start pythonw PYTHON/scheduler/run_scheduler.py
    # Docker: python PYTHON/scheduler/run_scheduler.py

Bu script AnatoliaX saat kurallarina gore tum zamanlanmis gorevleri baslatir.
"""
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

from scheduler.task_scheduler import TaskScheduler
from scheduler.anatoliax_jobs import register_all_jobs


def main():
    print("=" * 60)
    print("AnatoliaX Task Scheduler baslatiliyor...")
    print("=" * 60)

    sched = TaskScheduler()
    register_all_jobs(sched)
    sched.start()

    jobs = sched.list_jobs()
    print(f"\nToplam {len(jobs)} gorev kaydedildi:")
    for job in jobs:
        print(f"  - {job.get('id', 'N/A')} | Sonraki: {job.get('next_run', 'N/A')}")

    print("\nScheduler calisiyor. Durdurmak icin Ctrl+C")
    print("=" * 60)

    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nScheduler durduruluyor...")
        sched.shutdown()
        print("Tamamlandi.")


if __name__ == "__main__":
    main()
