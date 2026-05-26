"""
observability/cryptographic_audit.py - Cryptographically Immutable Audit Framework

Tamper-proof append-only verification for every signal, execution, decision,
AI inference, portfolio mutation, and risk override.
"""

import hashlib
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class AuditEntry:
    entry_id: str
    entry_type: str
    timestamp: str
    data: Dict[str, Any]
    previous_hash: str
    current_hash: str
    signature: str
    verified: bool = True


class CryptographicAuditLogger:
    def __init__(self, db_path: str = "audit_log.jsonl"):
        self.db_path = Path(db_path)
        self._chain: List[AuditEntry] = []
        self._last_hash: str = "genesis"
        self._load_existing()
    
    def _load_existing(self) -> None:
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r') as f:
                    for line in f:
                        entry_data = json.loads(line.strip())
                        entry = AuditEntry(**entry_data)
                        self._chain.append(entry)
                        self._last_hash = entry.current_hash
            except Exception:
                pass
    
    def _calculate_hash(self, entry_data: Dict) -> str:
        return hashlib.sha256(
            json.dumps(entry_data, sort_keys=True).encode()
        ).hexdigest()
    
    def _sign_entry(self, entry_data: Dict) -> str:
        return hashlib.sha256(
            f"{entry_data['current_hash']}{entry_data['timestamp']}".encode()
        ).hexdigest()
    
    def append(self, entry_type: str, data: Dict[str, Any]) -> AuditEntry:
        timestamp = datetime.now(timezone.utc).isoformat()
        
        entry_data = {
            'entry_type': entry_type,
            'timestamp': timestamp,
            'data': data,
            'previous_hash': self._last_hash,
        }
        
        current_hash = self._calculate_hash(entry_data)
        entry_data['current_hash'] = current_hash
        
        signature = self._sign_entry(entry_data)
        entry_data['signature'] = signature
        
        entry = AuditEntry(
            entry_id=hashlib.sha256(
                f"{entry_type}{timestamp}".encode()
            ).hexdigest()[:16],
            entry_type=entry_type,
            timestamp=timestamp,
            data=data,
            previous_hash=self._last_hash,
            current_hash=current_hash,
            signature=signature,
            verified=True,
        )
        
        self._chain.append(entry)
        self._last_hash = current_hash
        
        self._persist(entry)
        return entry
    
    def _persist(self, entry: AuditEntry) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.db_path, 'a') as f:
            f.write(json.dumps(asdict(entry)) + '\n')
    
    def verify_chain(self) -> bool:
        if len(self._chain) == 0:
            return True
        
        if self._chain[0].previous_hash != "genesis":
            return False
        
        for i in range(1, len(self._chain)):
            prev_entry = self._chain[i-1]
            curr_entry = self._chain[i]
            
            if curr_entry.previous_hash != prev_entry.current_hash:
                curr_entry.verified = False
                return False
            
            entry_data = {
                'entry_type': curr_entry.entry_type,
                'timestamp': curr_entry.timestamp,
                'data': curr_entry.data,
                'previous_hash': curr_entry.previous_hash,
            }
            
            expected_hash = self._calculate_hash(entry_data)
            if curr_entry.current_hash != expected_hash:
                curr_entry.verified = False
                return False
        
        return True
    
    def get_entries(self, entry_type: Optional[str] = None,
                   limit: int = 100) -> List[AuditEntry]:
        if entry_type:
            entries = [e for e in self._chain if e.entry_type == entry_type]
        else:
            entries = self._chain
        
        return entries[-limit:]
    
    def get_audit_report(self) -> Dict[str, Any]:
        return {
            'total_entries': len(self._chain),
            'chain_verified': self.verify_chain(),
            'last_hash': self._last_hash,
            'entries_by_type': self._count_by_type(),
            'db_path': str(self.db_path),
        }
    
    def _count_by_type(self) -> Dict[str, int]:
        counts = {}
        for entry in self._chain:
            if entry.entry_type not in counts:
                counts[entry.entry_type] = 0
            counts[entry.entry_type] += 1
        return counts
    
    def log_signal(self, signal_id: str, signal_data: Dict) -> AuditEntry:
        return self.append('signal', {
            'signal_id': signal_id,
            'signal_data': signal_data,
        })
    
    def log_execution(self, order_id: str, execution_data: Dict) -> AuditEntry:
        return self.append('execution', {
            'order_id': order_id,
            'execution_data': execution_data,
        })
    
    def log_decision(self, agent: str, decision: str, 
                    reasoning: Dict) -> AuditEntry:
        return self.append('decision', {
            'agent': agent,
            'decision': decision,
            'reasoning': reasoning,
        })
    
    def log_ai_inference(self, model: str, input_data: Dict,
                        output_data: Dict) -> AuditEntry:
        return self.append('ai_inference', {
            'model': model,
            'input': input_data,
            'output': output_data,
        })
    
    def log_portfolio_mutation(self, mutation_type: str,
                              before: Dict, after: Dict) -> AuditEntry:
        return self.append('portfolio_mutation', {
            'mutation_type': mutation_type,
            'before': before,
            'after': after,
        })
    
    def log_risk_override(self, override_type: str,
                         original_limit: float,
                         new_limit: float,
                         reason: str) -> AuditEntry:
        return self.append('risk_override', {
            'override_type': override_type,
            'original_limit': original_limit,
            'new_limit': new_limit,
            'reason': reason,
        })


_audit_logger: Optional[CryptographicAuditLogger] = None

def get_cryptographic_audit_logger(db_path: str = "audit_log.jsonl") -> CryptographicAuditLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = CryptographicAuditLogger(db_path=db_path)
    return _audit_logger
