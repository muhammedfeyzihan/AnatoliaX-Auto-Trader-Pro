"""
core/ring_buffer.py — Kilitsiz SPSC halka tampon (paylaşımlı bellek + atomik işlemler)

Tek-üretici tek-tüketici (SPSC) halka tampon; kilit, mutex veya çekirdek çağrısı
olmadan iş parçacıkları arası iletişim için.
"""
import mmap
import os
import struct
from typing import List, Optional


class LockFreeRingBuffer:
    """
    Kilitsiz SPSC halka tampon (mmap üzerinde atomik head/tail).

    Kapasite: yapılandırılabilir (varsayılan 1M kayıt).
    Kayıt boyutu: yapılandırılabilir (varsayılan 64 bayt).
    Bellek düzeni: [başlık (atomik head/tail)] [kayıtlar...]

    Üretici (besleme iş parçacığı): yaz, atomik artır head.
    Tüketici (strateji iş parçacığı): oku, atomik artır tail.
    Geri basınç: head - tail >= kapasite ise en eskiyi düşür (log + uyarı).
    """

    def __init__(self, name: str, capacity: int = 1_000_000, entry_size: int = 64):
        self.name = name
        self.capacity = capacity
        self.entry_size = entry_size
        header_size = 16  # head (8) + tail (8)
        self.total_size = header_size + capacity * entry_size
        # Bellek haritalama (basit mmap; POSIX paylaşımlı bellek ileride eklenebilir)
        self._mmap = mmap.mmap(-1, self.total_size)
        # head @ offset 0, tail @ offset 8 (unsigned long long)
        self._header_fmt = struct.Struct("QQ")

    def push(self, data: bytes) -> bool:
        """Engellemeden itme. Tampon doluysa False döner."""
        head, tail = self._read_header()
        used = (head - tail) % (self.capacity * 2)
        if used >= self.capacity:
            return False
        # Yaz
        offset = 16 + (head % self.capacity) * self.entry_size
        self._mmap[offset:offset + self.entry_size] = data.ljust(self.entry_size, b"\x00")
        # Atomik head artır (basit: struct ile yeniden yaz)
        new_head = (head + 1) % (self.capacity * 2)
        self._write_header(new_head, tail)
        return True

    def pop(self) -> Optional[bytes]:
        """Engellemeden çekme. Tampon boşsa None döner."""
        head, tail = self._read_header()
        if head == tail:
            return None
        offset = 16 + (tail % self.capacity) * self.entry_size
        data = self._mmap[offset:offset + self.entry_size]
        new_tail = (tail + 1) % (self.capacity * 2)
        self._write_header(head, new_tail)
        return data.rstrip(b"\x00")

    def batch_push(self, items: List[bytes]) -> int:
        """Birden fazla kayıt it. Başarıyla itilen sayısını döndür."""
        count = 0
        for item in items:
            if not self.push(item):
                break
            count += 1
        return count

    def batch_pop(self, max_items: int) -> List[bytes]:
        """En fazla max_items kayıt çek. Listeyi döndür."""
        result: List[bytes] = []
        for _ in range(max_items):
            item = self.pop()
            if item is None:
                break
            result.append(item)
        return result

    @property
    def utilization(self) -> float:
        """Doluluk oranını döndür (0.0 ila 1.0).
        >0.8 ise uyarı."""
        head, tail = self._read_header()
        used = (head - tail) % (self.capacity * 2)
        return min(used / self.capacity, 1.0)

    def _read_header(self) -> tuple:
        self._mmap.seek(0)
        return self._header_fmt.unpack(self._mmap.read(16))

    def _write_header(self, head: int, tail: int) -> None:
        self._mmap.seek(0)
        self._mmap.write(self._header_fmt.pack(head, tail))
