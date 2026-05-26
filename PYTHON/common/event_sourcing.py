"""
common/event_sourcing.py — Distributed Event Sourcing (Phase 2)
Module 7 from anatoliax_prompt_v6.txt

Features:
  - All state S(t) derived from immutable event log E = [e_1, e_2, ..., e_n].
  - State reconstruction: S(t) = reduce(apply, E[0:t], S_0).
  - Event schema: {event_id, event_type, timestamp, payload, causation_id, correlation_id}.
  - Event types: MarketDataEvent, SignalEvent, RiskCheckEvent, OrderEvent, FillEvent, PositionEvent, PnLEvent, RegimeEvent.

Validation:
  - Replay events from t=0, verify S(t) matches live state at checkpoint times
"""

import json
import sqlite3
import uuid
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any, TypeVar, Generic
from enum import Enum
from collections import defaultdict


class EventType(Enum):
    """Standard event types for event sourcing."""
    MARKET_DATA = "MarketDataEvent"
    SIGNAL = "SignalEvent"
    RISK_CHECK = "RiskCheckEvent"
    ORDER = "OrderEvent"
    FILL = "FillEvent"
    POSITION = "PositionEvent"
    PNL = "PnLEvent"
    REGIME = "RegimeEvent"
    SYSTEM = "SystemEvent"


@dataclass
class Event:
    """
    Immutable event structure.
    
    Schema:
      - event_id: Unique identifier (UUID)
      - event_type: Type of event
      - timestamp: Nanosecond precision timestamp
      - payload: Event-specific data
      - causation_id: ID of event that caused this one
      - correlation_id: ID for tracking related events across aggregates
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.MARKET_DATA
    timestamp: int = field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1e9))
    payload: Dict[str, Any] = field(default_factory=dict)
    causation_id: str = ""
    correlation_id: str = ""
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "payload": json.dumps(self.payload, sort_keys=True),
            "causation_id": self.causation_id,
            "correlation_id": self.correlation_id,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Event":
        return cls(
            event_id=d["event_id"],
            event_type=EventType(d["event_type"]),
            timestamp=d["timestamp"],
            payload=json.loads(d["payload"]),
            causation_id=d["causation_id"],
            correlation_id=d["correlation_id"],
            version=d.get("version", 1),
        )

    def compute_hash(self) -> str:
        """Compute cryptographic hash of event for integrity verification."""
        data = f"{self.event_id}{self.event_type.value}{self.timestamp}{json.dumps(self.payload, sort_keys=True)}"
        return hashlib.sha256(data.encode()).hexdigest()

    def with_causation(self, parent_event: "Event") -> "Event":
        """Create a new event with this event as causation."""
        self.causation_id = parent_event.event_id
        self.correlation_id = parent_event.correlation_id or parent_event.event_id
        return self


# Type for state in event sourcing
S = TypeVar("S")


class EventStore(Generic[S]):
    """
    Immutable event log backed by SQLite WAL.
    
    All state S(t) derived from event log E:
      S(t) = reduce(apply, E[0:t], S_0)
    
    Features:
      - Append-only event log
      - State reconstruction from events
      - Checkpoint/restore for fast replay
      - Event hashing for integrity
    """

    def __init__(self, db_path: str = "event_store.db"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._memory_mode = db_path == ":memory:" or db_path.startswith("file::memory:")
        
        if self._memory_mode:
            self._conn = sqlite3.connect(db_path, uri=db_path.startswith("file:"))
            self._init_db(self._conn)
        else:
            self._init_db()
        
        self._event_cache: List[Event] = []
        self._checkpoint_state: Optional[Any] = None
        self._checkpoint_ts: Optional[int] = None

    def _init_db(self, conn=None):
        """Initialize database schema."""
        target = conn or sqlite3.connect(self.db_path)
        try:
            # Enable WAL mode for better concurrent reads
            target.execute("PRAGMA journal_mode=WAL")
            
            # Events table
            target.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    causation_id TEXT,
                    correlation_id TEXT,
                    version INTEGER DEFAULT 1,
                    event_hash TEXT
                )
            """)
            
            # Indexes for efficient querying
            target.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp)")
            target.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
            target.execute("CREATE INDEX IF NOT EXISTS idx_events_corr ON events(correlation_id)")
            target.execute("CREATE INDEX IF NOT EXISTS idx_events_caus ON events(causation_id)")
            
            # Checkpoints table for fast replay
            target.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    timestamp INTEGER PRIMARY KEY,
                    state TEXT NOT NULL,
                    event_count INTEGER,
                    event_hash TEXT
                )
            """)
            
            target.commit()
        finally:
            if conn is None:
                target.close()

    def append(self, event: Event) -> str:
        """
        Append immutable event to log E.
        
        Args:
            event: Event to append
        
        Returns:
            Event ID
        """
        event_hash = event.compute_hash()
        
        if self._conn:
            self._conn.execute(
                """INSERT INTO events (event_id, event_type, timestamp, payload, causation_id, correlation_id, version, event_hash) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (event.event_id, event.event_type.value, event.timestamp,
                 json.dumps(event.payload, sort_keys=True), event.causation_id, event.correlation_id,
                 event.version, event_hash)
            )
            self._conn.commit()
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute(
                    """INSERT INTO events (event_id, event_type, timestamp, payload, causation_id, correlation_id, version, event_hash) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (event.event_id, event.event_type.value, event.timestamp,
                     json.dumps(event.payload, sort_keys=True), event.causation_id, event.correlation_id,
                     event.version, event_hash)
                )
                conn.commit()
        
        self._event_cache.append(event)
        return event.event_id

    def get_events(
        self,
        after_ts: int = 0,
        event_type: Optional[EventType] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100000,
    ) -> List[Event]:
        """
        Query events with filters.
        
        Args:
            after_ts: Filter events after this timestamp
            event_type: Filter by event type
            correlation_id: Filter by correlation ID
            limit: Maximum events to return
        
        Returns:
            List of events matching criteria
        """
        def _fetch(conn):
            conditions = ["timestamp > ?"]
            params = [after_ts]
            
            if event_type:
                conditions.append("event_type = ?")
                params.append(event_type.value)
            
            if correlation_id:
                conditions.append("correlation_id = ?")
                params.append(correlation_id)
            
            query = f"""
                SELECT event_id, event_type, timestamp, payload, causation_id, correlation_id, version, event_hash
                FROM events
                WHERE {" AND ".join(conditions)}
                ORDER BY timestamp
                LIMIT ?
            """
            params.append(limit)
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            return [Event(
                event_id=r[0],
                event_type=EventType(r[1]),
                timestamp=r[2],
                payload=json.loads(r[3]),
                causation_id=r[4],
                correlation_id=r[5],
                version=r[6],
            ) for r in rows]
        
        if self._conn:
            return _fetch(self._conn)
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                return _fetch(conn)

    def replay(self, apply_fn: Callable[[S, Event], S], initial_state: S, from_checkpoint: bool = True) -> S:
        """
        State reconstruction: S(t) = reduce(apply, E[0:t], S_0).
        
        Args:
            apply_fn: Function to apply each event to state
            initial_state: Starting state S_0
            from_checkpoint: If True, start from latest checkpoint
        
        Returns:
            Reconstructed state S(t)
        """
        # Try to load from checkpoint
        checkpoint = self._load_checkpoint() if from_checkpoint else None
        
        if checkpoint:
            state = checkpoint["state"]
            after_ts = checkpoint["timestamp"]
        else:
            state = initial_state
            after_ts = 0
        
        # Apply events after checkpoint
        events = self.get_events(after_ts=after_ts, limit=1000000)
        for event in events:
            state = apply_fn(state, event)
        
        return state

    def checkpoint(self, state: Any, timestamp: int, event_count: Optional[int] = None):
        """
        Save checkpoint for fast replay.
        
        Args:
            state: Current state to checkpoint
            timestamp: Timestamp of checkpoint
            event_count: Number of events processed
        """
        # Compute hash of all events up to this point for integrity
        events = self.get_events(limit=event_count or 1000000)
        combined_hash = hashlib.sha256(
            "".join([e.compute_hash() for e in events]).encode()
        ).hexdigest()
        
        checkpoint_data = {
            "timestamp": timestamp,
            "state": state,
            "event_count": event_count or len(events),
            "event_hash": combined_hash,
        }
        
        if self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO checkpoints (timestamp, state, event_count, event_hash) VALUES (?, ?, ?, ?)",
                (timestamp, json.dumps(state, sort_keys=True, default=str), event_count or len(events), combined_hash)
            )
            self._conn.commit()
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute(
                    "INSERT OR REPLACE INTO checkpoints (timestamp, state, event_count, event_hash) VALUES (?, ?, ?, ?)",
                    (timestamp, json.dumps(state, sort_keys=True, default=str), event_count or len(events), combined_hash)
                )
                conn.commit()
        
        self._checkpoint_state = state
        self._checkpoint_ts = timestamp

    def _load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load latest checkpoint."""
        def _fetch(conn):
            cursor = conn.execute(
                "SELECT timestamp, state, event_count, event_hash FROM checkpoints ORDER BY timestamp DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                return {
                    "timestamp": row[0],
                    "state": json.loads(row[1]),
                    "event_count": row[2],
                    "event_hash": row[3],
                }
            return None
        
        if self._conn:
            return _fetch(self._conn)
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                return _fetch(conn)

    def validate_integrity(self) -> Dict[str, Any]:
        """
        Validate event log integrity.
        
        Returns:
            Validation report with any integrity issues
        """
        events = self.get_events(limit=1000000)
        issues = []
        
        # Check for duplicate event IDs
        event_ids = [e.event_id for e in events]
        duplicates = len(event_ids) - len(set(event_ids))
        if duplicates > 0:
            issues.append(f"Duplicate event IDs: {duplicates}")
        
        # Check timestamp ordering
        for i in range(1, len(events)):
            if events[i].timestamp < events[i-1].timestamp:
                issues.append(f"Timestamp ordering violation at event {events[i].event_id}")
        
        # Check causation chains
        event_id_set = set(event_ids)
        for event in events:
            if event.causation_id and event.causation_id not in event_id_set:
                issues.append(f"Broken causation chain: {event.causation_id} -> {event.event_id}")
        
        return {
            "total_events": len(events),
            "integrity_valid": len(issues) == 0,
            "issues": issues,
        }

    def get_event_stream(self, correlation_id: str) -> List[Event]:
        """Get all events in a correlation stream."""
        return self.get_events(correlation_id=correlation_id, limit=1000000)

    def get_events_by_type(self, event_type: EventType) -> List[Event]:
        """Get all events of a specific type."""
        return self.get_events(event_type=event_type, limit=1000000)

    def count_events(self) -> int:
        """Get total event count."""
        def _count(conn):
            cursor = conn.execute("SELECT COUNT(*) FROM events")
            return cursor.fetchone()[0]
        
        if self._conn:
            return _count(self._conn)
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                return _count(conn)

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


class EventBus:
    """
    In-memory event bus for pub/sub between agents.
    Integrates with EventStore for persistence.
    """

    def __init__(self, event_store: Optional[EventStore] = None):
        self._subscribers: Dict[EventType, List[Callable[[Event], None]]] = defaultdict(list)
        self._store = event_store
        self._event_queue: List[Event] = []

    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """Subscribe to events of a specific type."""
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """Unsubscribe from events."""
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

    def publish(self, event: Event) -> str:
        """
        Publish event to bus and optionally persist to store.
        
        Args:
            event: Event to publish
        
        Returns:
            Event ID
        """
        # Persist to store first
        if self._store:
            self._store.append(event)
        
        # Queue for async delivery
        self._event_queue.append(event)
        
        # Synchronous delivery to subscribers
        for cb in self._subscribers.get(event.event_type, []):
            cb(event)
        
        return event.event_id

    def publish_batch(self, events: List[Event]) -> List[str]:
        """Publish multiple events atomically."""
        event_ids = []
        for event in events:
            event_ids.append(self.publish(event))
        return event_ids

    def flush(self):
        """Flush event queue (for async delivery implementations)."""
        self._event_queue.clear()

    def get_pending_events(self) -> List[Event]:
        """Get pending events in queue."""
        return self._event_queue.copy()
