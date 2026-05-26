"""
strategy_registry.py — Dynamic strategy loading/unloading + hot-reload.
K224: StrategyRegistry.

v3.3+: File watcher, hot-reload, plugin validation, rollback on failure.
"""
import importlib
import importlib.util
import os
import inspect
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class StrategyMeta:
    name: str = ""
    version: str = "1.0"
    description: str = ""
    author: str = ""
    timeframes: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    module_path: str = ""
    loaded_at: Optional[datetime] = None
    instance: Optional[Any] = None
    file_hash: str = ""  # v3.3: content hash for hot-reload detection
    last_modified: float = 0.0


class StrategyRegistry:
    """
    Dinamik strateji kayit defteri. Stratejileri runtime'da yukle/kaldir.
    v3.3: Hot-reload, file watcher, plugin validation, rollback.
    """

    def __init__(self, strategy_dir: Optional[str] = None, enable_hot_reload: bool = False):
        self._strategies: Dict[str, StrategyMeta] = {}
        self._strategy_dir = strategy_dir or os.path.join(os.path.dirname(__file__))
        self._enable_hot_reload = enable_hot_reload
        self._plugin_dir: Optional[Path] = None
        self._watch_interval_sec = 5.0
        self._validation_hooks: List[Callable[[StrategyMeta], Tuple[bool, str]]] = []
        self._rollback_cache: Dict[str, StrategyMeta] = {}  # Backup before reload

    def register(self, meta: StrategyMeta, instance: Any = None):
        """Manuel kayit."""
        meta.loaded_at = datetime.now(timezone.utc)
        if instance:
            meta.instance = instance
        self._strategies[meta.name] = meta

    def load_from_path(self, module_path: str, class_name: Optional[str] = None) -> StrategyMeta:
        """Dosya yolundan strateji yukle."""
        # Unique module name per load to bypass importlib caches on hot-reload
        unique_name = f"dynamic_strategy_{hashlib.sha256(module_path.encode()).hexdigest()[:8]}_{int(time.time()*1000)}"
        spec = importlib.util.spec_from_file_location(unique_name, module_path)
        if not spec or not spec.loader:
            raise ImportError(f"Modul yuklenemedi: {module_path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Auto-discover strategy class (prefer classes with "Strategy" in name, else fallback to any class)
        members = [name for name, obj in inspect.getmembers(mod) if inspect.isclass(obj)]
        candidates = [name for name in members if "Strategy" in name]
        cls_name = class_name or (candidates[0] if candidates else (members[0] if members else None))
        if not cls_name:
            raise ValueError(f"Strateji sinifi bulunamadi: {module_path}")

        cls = getattr(mod, cls_name)
        instance = cls() if not inspect.signature(cls).parameters else cls()
        meta = StrategyMeta(
            name=getattr(instance, "NAME", cls_name),
            version=getattr(instance, "VERSION", "1.0"),
            description=getattr(instance, "DESCRIPTION", ""),
            timeframes=getattr(instance, "TIMEFRAMES", []),
            params=getattr(instance, "DEFAULT_PARAMS", {}),
            module_path=module_path,
            instance=instance,
        )
        self._strategies[meta.name] = meta
        return meta

    def load_from_module(self, module_name: str, class_name: str) -> StrategyMeta:
        """Mevcut PYTHON paketinden yukle."""
        mod = importlib.import_module(module_name)
        cls = getattr(mod, class_name)
        instance = cls()
        meta = StrategyMeta(
            name=getattr(instance, "NAME", class_name),
            version=getattr(instance, "VERSION", "1.0"),
            description=getattr(instance, "DESCRIPTION", ""),
            timeframes=getattr(instance, "TIMEFRAMES", []),
            params=getattr(instance, "DEFAULT_PARAMS", {}),
            module_path=module_name,
            instance=instance,
        )
        self._strategies[meta.name] = meta
        return meta

    def unload(self, name: str) -> bool:
        if name in self._strategies:
            del self._strategies[name]
            return True
        return False

    def get(self, name: str) -> Optional[StrategyMeta]:
        return self._strategies.get(name)

    def list_strategies(self) -> List[str]:
        return list(self._strategies.keys())

    def get_all(self) -> Dict[str, StrategyMeta]:
        return self._strategies.copy()

    def run_strategy(self, name: str, data: Any, params: Optional[Dict] = None) -> Any:
        meta = self._strategies.get(name)
        if not meta or not meta.instance:
            raise ValueError(f"Strateji bulunamadi: {name}")
        run_method = getattr(meta.instance, "run", None) or getattr(meta.instance, "execute", None)
        if not run_method:
            raise ValueError(f"Stratejide run/execute metodu yok: {name}")
        return run_method(data, params or {})

    def reset(self):
        self._strategies.clear()

    # ------------------------------------------------------------------
    # v3.3: Hot-reload
    # ------------------------------------------------------------------
    def set_plugin_dir(self, path: str):
        self._plugin_dir = Path(path)
        self._plugin_dir.mkdir(parents=True, exist_ok=True)

    def scan_plugins(self) -> List[StrategyMeta]:
        """Auto-discover and load all .py files in plugin directory."""
        loaded = []
        if not self._plugin_dir:
            return loaded
        for fpath in self._plugin_dir.rglob("*.py"):
            try:
                meta = self.load_from_path(str(fpath))
                loaded.append(meta)
            except Exception:
                continue
        return loaded

    def _file_hash(self, fpath: str) -> str:
        try:
            content = Path(fpath).read_bytes()
            return hashlib.sha256(content).hexdigest()[:16]
        except Exception:
            return ""

    def _last_modified(self, fpath: str) -> float:
        try:
            return Path(fpath).stat().st_mtime
        except Exception:
            return 0.0

    def _load_from_source(self, fpath: str) -> StrategyMeta:
        """Bypass importlib caches by compiling source directly. Used by hot-reload."""
        content = Path(fpath).read_text(encoding="utf-8")
        code = compile(content, fpath, "exec")
        namespace = {}
        exec(code, namespace)
        # Auto-discover class
        classes = [v for v in namespace.values() if inspect.isclass(v)]
        candidates = [c for c in classes if "Strategy" in c.__name__]
        cls = candidates[0] if candidates else (classes[0] if classes else None)
        if cls is None:
            raise ValueError(f"Strateji sinifi bulunamadi: {fpath}")
        instance = cls() if not inspect.signature(cls).parameters else cls()
        return StrategyMeta(
            name=getattr(instance, "NAME", cls.__name__),
            version=getattr(instance, "VERSION", "1.0"),
            description=getattr(instance, "DESCRIPTION", ""),
            timeframes=getattr(instance, "TIMEFRAMES", []),
            params=getattr(instance, "DEFAULT_PARAMS", {}),
            module_path=fpath,
            instance=instance,
        )

    def check_hot_reload(self) -> List[dict]:
        """Check all loaded strategies for file changes. Returns list of reloaded strategies."""
        reloaded = []
        for name, meta in list(self._strategies.items()):
            if not meta.module_path or not Path(meta.module_path).exists():
                continue
            current_hash = self._file_hash(meta.module_path)
            current_mtime = self._last_modified(meta.module_path)
            if current_hash != meta.file_hash or current_mtime > meta.last_modified:
                # Backup before reload
                self._rollback_cache[name] = meta
                try:
                    new_meta = self._load_from_source(meta.module_path)
                    new_meta.file_hash = current_hash
                    new_meta.last_modified = current_mtime
                    self._strategies[name] = new_meta
                    reloaded.append({"name": name, "status": "RELOADED", "old_version": meta.version, "new_version": new_meta.version})
                except Exception as e:
                    # Rollback on failure
                    old = self._rollback_cache.pop(name, None)
                    if old:
                        self._strategies[name] = old
                    reloaded.append({"name": name, "status": "ROLLBACK", "error": str(e)})
        return reloaded

    def auto_watch_loop(self, interval_sec: Optional[float] = None):
        """Blocking watch loop. Use in a background thread."""
        import threading
        interval = interval_sec or self._watch_interval_sec
        def _loop():
            while self._enable_hot_reload:
                self.check_hot_reload()
                time.sleep(interval)
        threading.Thread(target=_loop, daemon=True).start()

    def add_validation_hook(self, hook: Callable[[StrategyMeta], Tuple[bool, str]]):
        """Add a custom validation hook run before loading a strategy."""
        self._validation_hooks.append(hook)

    def _validate(self, meta: StrategyMeta) -> Tuple[bool, str]:
        for hook in self._validation_hooks:
            ok, reason = hook(meta)
            if not ok:
                return False, reason
        # Default validations
        if not meta.name:
            return False, "Missing strategy name"
        if meta.instance is None:
            return False, "Strategy instance is None"
        if not hasattr(meta.instance, "run") and not hasattr(meta.instance, "execute"):
            return False, "Strategy must have run() or execute() method"
        return True, "OK"
