"""
human_gate.py — Insan onayi sistemi (5 onay seviyesi)
"""
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional


class ApprovalLevel(Enum):
    LEVEL_1_AUTO = auto()      # Otomatik (test coverage >%80)
    LEVEL_2_PEER = auto()      # Akran incelemesi (Kimi/Claude)
    LEVEL_3_SENIOR = auto()    # Kidemli muhendis onayi
    LEVEL_4_LEAD = auto()      # Takim lideri onayi (kritik degisiklik)
    LEVEL_5_ARCHITECT = auto() # Mimar onayi (altyapi degisikligi)


@dataclass
class ApprovalRequest:
    change_id: str
    level: ApprovalLevel
    description: str
    requester: str
    approved_by: List[str]
    status: str  # pending, approved, rejected


class HumanGate:
    """
    Insan onayi sistemi.

    Onay seviyeleri:
    - L1: Otomatik (test >%80, coverage >%70, 0 guvenlik uyarisi)
    - L2: Akran incelemesi (Kimi/Claude)
    - L3: Kidemli muhendis onayi
    - L4: Takim lideri onayi (kritik degisiklikler)
    - L5: Mimar onayi (altyapi degisiklikleri)

    Bildirim:
    - Telegram: anlik mesaj
    - E-posta: gunluk ozet
    """

    def __init__(self):
        self._requests: dict = {}

    def request_approval(self, change_id: str, level: ApprovalLevel, description: str,
                         requester: str) -> ApprovalRequest:
        req = ApprovalRequest(
            change_id=change_id,
            level=level,
            description=description,
            requester=requester,
            approved_by=[],
            status="pending",
        )
        self._requests[change_id] = req
        self._notify(req)
        return req

    def approve(self, change_id: str, approver: str) -> bool:
        req = self._requests.get(change_id)
        if not req:
            return False
        if approver not in req.approved_by:
            req.approved_by.append(approver)
        if self._is_fully_approved(req):
            req.status = "approved"
        return True

    def reject(self, change_id: str, approver: str, reason: str) -> bool:
        req = self._requests.get(change_id)
        if not req:
            return False
        req.status = f"rejected by {approver}: {reason}"
        return True

    def _is_fully_approved(self, req: ApprovalRequest) -> bool:
        required = {ApprovalLevel.LEVEL_1_AUTO: 0, ApprovalLevel.LEVEL_2_PEER: 1,
                      ApprovalLevel.LEVEL_3_SENIOR: 1, ApprovalLevel.LEVEL_4_LEAD: 1,
                      ApprovalLevel.LEVEL_5_ARCHITECT: 1}
        return len(req.approved_by) >= required.get(req.level, 1)

    def _notify(self, req: ApprovalRequest) -> None:
        # Yer tutucu: Telegram/e-posta bildirimi ileride implemente edilecek
        pass
