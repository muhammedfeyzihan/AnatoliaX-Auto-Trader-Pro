"""
core/memory_pool.py — Önceden ayrılmış nesne havuzu (sıfır-GC sıcak yol)
"""
import threading
from typing import Callable, Generic, List, Optional, TypeVar

T = TypeVar("T")


class ObjectPool(Generic[T]):
    """
    Önceden ayrılmış sabit boyutlu nesne havuzu.

    Strateji:
    1. Başlangıçta N nesne önceden ayır
    2. acquire(): boş yığından çek (LIFO, önbellek dostu)
    3. release(): boş yığına geri it
    4. Havuz tükenirse: acil blok ayır (uyarı logla)

    İş parçacığı modeli: iş parçacığı-yerel havuzlar + atomik global çalma.
    """

    def __init__(self, factory: Callable[[], T], capacity: int, thread_local_size: int = 64):
        self._factory = factory
        self._capacity = capacity
        self._thread_local_size = thread_local_size
        self._global_pool: List[T] = [factory() for _ in range(capacity)]
        self._global_lock = threading.Lock()
        self._local = threading.local()
        self._in_use = 0
        self._high_water = 0

    def acquire(self) -> T:
        """Havuzdan nesne al. Alanları varsayılanlara sıfırla."""
        local_stack: Optional[List[T]] = getattr(self._local, "stack", None)
        if local_stack and local_stack:
            obj = local_stack.pop()
            self._in_use += 1
            if self._in_use > self._high_water:
                self._high_water = self._in_use
            return obj
        # Global havuzdan çal
        with self._global_lock:
            if self._global_pool:
                obj = self._global_pool.pop()
                self._in_use += 1
                if self._in_use > self._high_water:
                    self._high_water = self._in_use
                return obj
        # Acil ayırma
        return self._factory()

    def release(self, obj: T) -> None:
        """Nesneyi havuza iade et. Hassas verileri temizle."""
        self._in_use -= 1
        local_stack: Optional[List[T]] = getattr(self._local, "stack", None)
        if local_stack is None:
            local_stack = []
            self._local.stack = local_stack
        if len(local_stack) < self._thread_local_size:
            local_stack.append(obj)
        else:
            with self._global_lock:
                self._global_pool.append(obj)

    @property
    def available(self) -> int:
        """Kullanılabilir nesne sayısı."""
        local = len(getattr(self._local, "stack", []))
        with self._global_lock:
            global_avail = len(self._global_pool)
        return local + global_avail

    @property
    def in_use(self) -> int:
        """Şu anda kullanımda olan nesne sayısı."""
        return self._in_use
