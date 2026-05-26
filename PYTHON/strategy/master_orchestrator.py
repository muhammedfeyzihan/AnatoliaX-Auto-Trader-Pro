"""
PYTHON/strategy/master_orchestrator.py — Master System Orchestrator

Tum 30 kurumsal ozelligi koordine eden ana sistem.

Responsibilities:
- Real-time decision making
- Continuous learning loop
- Performance monitoring
- Auto-adjustment based on market regime
- Feature coordination
- System health monitoring
"""
import asyncio
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import numpy as np


@dataclass
class SystemState:
    """Sistem durumu."""
    status: str = "initializing"  # initializing, running, paused, stopped
    regime: str = "unknown"
    mode: str = "balanced"
    active_trades: int = 0
    daily_pnl: float = 0.0
    daily_pnl_pct: float = 0.0
    total_pnl: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    health_score: float = 100.0
    active_features: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class OrchestratorConfig:
    """Orchestrator yapilandirmasi."""
    symbols: List[str] = field(default_factory=lambda: ["THYAO", "GARAN", "AKBNK", "EREGL", "TUPRS"])
    base_capital: float = 100000.0
    max_daily_loss_pct: float = 2.0
    target_daily_profit_pct: float = 1.0
    enable_auto_trading: bool = False
    enable_paper_trading: bool = True
    data_refresh_interval_sec: int = 60
    risk_check_interval_sec: int = 30
    learning_interval_sec: int = 300
    persistence_path: str = "PYTHON/data/orchestrator_state.json"


class MasterOrchestrator:
    """
    Master System Orchestrator.
    
    Coordinates all 30 institutional features:
    
    Core Features:
    1. Exchange Failure Simulation
    2. Nanosecond Tick Replay
    3. Adaptive Portfolio Hedging
    4. AI Meta-Learning
    5. Liquidity Intelligence
    6. Regime Detection AI
    7. Macro-Event Intelligence
    8. Chaos Engineering
    9. Self-Healing Infrastructure
    10. Cryptographic Audit
    
    Risk Features:
    11. Position Sizing Pro
    12. Crisis Correlation
    13. Synthetic Market Generator
    14. Explainable AI
    15. Multi-Agent Consensus
    16. Exchange Defense
    17. Military Secret Management
    18. Distributed Observability
    19. Institutional Execution
    20. Slippage & TCA
    
    Protection Features:
    21. Capital Preservation
    22. Distributed AI Memory
    23. Institutional Backtest
    24. Options Risk
    25. AI Execution Surveillance
    26. Distributed Data Validation
    27. Adaptive Leverage
    28. Institutional Portfolio
    29. Strategy Sandboxing
    30. AI Governance
    """
    
    def __init__(self, config: OrchestratorConfig = None):
        self.config = config or OrchestratorConfig()
        self.state = SystemState()
        self._modules: Dict[str, Any] = {}
        self._strategies: Dict[str, Any] = {}
        self._knowledge_base = None
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._event_log: List[Dict] = []
        self._performance_history: List[Dict] = []
    
    def register_module(self, name: str, module: Any) -> None:
        """Module kaydet."""
        self._modules[name] = module
        self.state.active_features = len(self._modules)
    
    def register_strategy(self, name: str, strategy: Any) -> None:
        """Strateji kaydet."""
        self._strategies[name] = strategy
    
    def set_knowledge_base(self, kb: Any) -> None:
        """Knowledge base ayarla."""
        self._knowledge_base = kb
    
    def _log_event(self, event_type: str, message: str, data: Dict = None) -> None:
        """Olay kaydet."""
        event = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': event_type,
            'message': message,
            'data': data or {}
        }
        self._event_log.append(event)
        
        # Cryptographic audit logging
        audit_module = self._modules.get('cryptographic_audit')
        if audit_module and hasattr(audit_module, 'log'):
            audit_module.log(event)
    
    def _update_system_state(self) -> None:
        """Sistem durumunu guncelle."""
        # Calculate total PnL from performance history
        if self._performance_history:
            self.state.total_pnl = sum(t.get('pnl', 0) for t in self._performance_history)
            self.state.total_trades = len(self._performance_history)
            
            # Calculate win rate
            wins = sum(1 for t in self._performance_history if t.get('pnl', 0) > 0)
            self.state.win_rate = wins / len(self._performance_history)
            
            # Calculate Sharpe ratio
            pnls = [t.get('pnl', 0) for t in self._performance_history]
            if len(pnls) > 1 and np.std(pnls) > 0:
                self.state.sharpe_ratio = np.mean(pnls) / np.std(pnls)
        
        # Get performance stats from optimal strategy
        optimal_strategy = self._strategies.get('optimal_profit')
        if optimal_strategy and hasattr(optimal_strategy, 'get_performance_stats'):
            stats = optimal_strategy.get_performance_stats()
            self.state.total_trades = stats.get('total_trades', self.state.total_trades)
            self.state.sharpe_ratio = stats.get('sharpe_ratio', self.state.sharpe_ratio)
            self.state.max_drawdown = stats.get('max_drawdown', self.state.max_drawdown)
            self.state.win_rate = stats.get('win_rate', self.state.win_rate)
            self.state.total_pnl = stats.get('total_pnl', self.state.total_pnl)
        
        # Calculate daily PnL
        self.state.daily_pnl = self._calculate_daily_pnl()
        self.state.daily_pnl_pct = (self.state.daily_pnl / self.config.base_capital) * 100
        
        # Get regime
        regime_detector = self._modules.get('regime_detector')
        if regime_detector and hasattr(regime_detector, 'get_current_regime'):
            self.state.regime = regime_detector.get_current_regime()
        
        # Get mode from optimal strategy
        if optimal_strategy and hasattr(optimal_strategy, '_mode'):
            self.state.mode = optimal_strategy._mode.value
        
        # Count active trades
        if optimal_strategy and hasattr(optimal_strategy, '_active_trades'):
            self.state.active_trades = len(optimal_strategy._active_trades)
        
        # Calculate health score
        self.state.health_score = self._calculate_health_score()
        
        self.state.last_update = datetime.now(timezone.utc)
    
    def _calculate_daily_pnl(self) -> float:
        """Gunluk PnL hesapla."""
        today = datetime.now(timezone.utc).date()
        daily_pnl = 0.0
        
        for trade in self._performance_history:
            trade_date = datetime.fromisoformat(trade['timestamp']).date()
            if trade_date == today:
                daily_pnl += trade.get('pnl', 0)
        
        return daily_pnl
    
    def _calculate_health_score(self) -> float:
        """
        Sistem saglik skoru hesapla.
        
        Factors:
        - Drawdown level
        - Daily PnL vs target
        - Error rate
        - Module availability
        """
        score = 100.0
        
        # Drawdown penalty (more aggressive)
        if self.state.max_drawdown > 0.05:
            score -= 25
        elif self.state.max_drawdown > 0.03:
            score -= 15
        elif self.state.max_drawdown > 0.02:
            score -= 8
        elif self.state.max_drawdown > 0.01:
            score -= 3
        
        # Daily loss penalty (more aggressive)
        if self.state.daily_pnl_pct < -self.config.max_daily_loss_pct:
            score -= 35
        elif self.state.daily_pnl_pct < 0:
            score -= 15
        
        # Error penalty (more aggressive)
        error_penalty = len(self.state.errors) * 8
        score -= min(error_penalty, 40)
        
        # Module availability bonus
        module_bonus = min(self.state.active_features / 30 * 10, 10)
        score += module_bonus
        
        return max(0, min(100, score))
    
    def _check_system_health(self) -> bool:
        """Sistem sagligini kontrol et."""
        # Critical checks
        if self.state.health_score < 50:
            self._log_event("HEALTH_CRITICAL", f"Health score: {self.state.health_score}")
            return False
        
        if self.state.daily_pnl_pct < -self.config.max_daily_loss_pct:
            self._log_event("DAILY_LOSS_LIMIT", f"Daily loss: {self.state.daily_pnl_pct:.2f}%")
            return False
        
        if self.state.max_drawdown > self.config.max_daily_loss_pct * 2:
            self._log_event("DRAWDOWN_LIMIT", f"Max drawdown: {self.state.max_drawdown:.2f}%")
            return False
        
        # Check critical modules
        critical_modules = ['risk_engine', 'execution_engine', 'capital_preservation']
        for mod in critical_modules:
            if mod not in self._modules:
                self._log_event("MODULE_MISSING", f"Critical module missing: {mod}")
                return False
        
        return True
    
    async def _data_refresh_loop(self) -> None:
        """Veri yenileme dongusu."""
        while self._running:
            try:
                # Update market data for all symbols
                for symbol in self.config.symbols:
                    self._log_event("DATA_REFRESH", f"Refreshing {symbol}")
                
                await asyncio.sleep(self.config.data_refresh_interval_sec)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._log_event("DATA_ERROR", str(e))
                await asyncio.sleep(5)
    
    async def _risk_check_loop(self) -> None:
        """Risk kontrol dongusu."""
        while self._running:
            try:
                # Check capital preservation
                capital_preservation = self._modules.get('capital_preservation')
                if capital_preservation and hasattr(capital_preservation, 'check'):
                    status = capital_preservation.check()
                    if not status.get('allowed', True):
                        self._log_event("RISK_ALERT", status.get('reason', 'Risk limit exceeded'))
                        self.state.errors.append(status.get('reason', 'Risk limit'))
                
                self._update_system_state()
                
                await asyncio.sleep(self.config.risk_check_interval_sec)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._log_event("RISK_ERROR", str(e))
                await asyncio.sleep(5)
    
    async def _learning_loop(self) -> None:
        """Ogrenme dongusu."""
        while self._running:
            try:
                # Meta-learning update
                meta_learner = self._modules.get('meta_learner')
                if meta_learner and hasattr(meta_learner, 'periodic_update'):
                    meta_learner.periodic_update(self._performance_history)
                
                # Knowledge base cleanup
                if self._knowledge_base:
                    self._knowledge_base.clear_old(days=30)
                
                self._log_event("LEARNING_UPDATE", "Periodic learning update completed")
                
                await asyncio.sleep(self.config.learning_interval_sec)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._log_event("LEARNING_ERROR", str(e))
                await asyncio.sleep(5)
    
    async def _self_healing_loop(self) -> None:
        """Kendini iyilestirme dongusu."""
        while self._running:
            try:
                self_healing = self._modules.get('self_healing')
                if self_healing and hasattr(self_healing, 'check_and_repair'):
                    issues = self_healing.check_and_repair()
                    if issues:
                        self._log_event("SELF_HEALING", f"Fixed {len(issues)} issues", {'issues': issues})
                        self.state.errors = [e for e in self.state.errors if e not in issues]
                
                await asyncio.sleep(300)  # 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._log_event("HEALING_ERROR", str(e))
                await asyncio.sleep(60)
    
    def initialize(self) -> None:
        """
        Sistemi baslat.
        
        Loads all modules and strategies.
        """
        self._log_event("INIT", "Initializing Master Orchestrator")
        
        # Load persistence
        self._load_state()
        
        # Validate modules
        required_modules = [
            'regime_detector', 'meta_learner', 'risk_engine',
            'execution_engine', 'liquidity_intelligence',
            'macro_intelligence', 'capital_preservation',
            'position_sizing', 'portfolio_optimizer',
            'agent_council', 'explainable_ai', 'cryptographic_audit'
        ]
        
        missing = [m for m in required_modules if m not in self._modules]
        if missing:
            self._log_event("INIT_WARNING", f"Missing modules: {missing}")
        
        # Initialize optimal strategy
        optimal_strategy = self._strategies.get('optimal_profit')
        if optimal_strategy:
            optimal_strategy.initialize(
                modules=self._modules,
                knowledge_base=self._knowledge_base
            )
        
        self.state.status = "initialized"
        self._log_event("INIT_COMPLETE", f"Initialized with {len(self._modules)} modules")
    
    def _load_state(self) -> None:
        """Persistan durum yukle."""
        path = Path(self.config.persistence_path)
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._performance_history = data.get('performance_history', [])
                self._event_log = data.get('event_log', [])[-1000:]  # Keep last 1000
            except Exception:
                pass
    
    def _save_state(self) -> None:
        """Persistan durum kaydet."""
        path = Path(self.config.persistence_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'performance_history': self._performance_history[-10000:],  # Keep last 10000
            'event_log': self._event_log[-1000:],
            'state': {
                'status': self.state.status,
                'total_pnl': self.state.total_pnl,
                'total_trades': self.state.total_trades,
                'sharpe_ratio': self.state.sharpe_ratio,
                'last_update': self.state.last_update.isoformat()
            }
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    async def start(self) -> None:
        """
        Sistemi calistir.
        
        Starts all background loops.
        """
        if self._running:
            return
        
        self._running = True
        self.state.status = "running"
        self._log_event("START", "System started")
        
        # Start background tasks
        self._tasks = [
            asyncio.create_task(self._data_refresh_loop()),
            asyncio.create_task(self._risk_check_loop()),
            asyncio.create_task(self._learning_loop()),
            asyncio.create_task(self._self_healing_loop())
        ]
        
        self._log_event("LOOPS_STARTED", f"Started {len(self._tasks)} background loops")
    
    async def stop(self) -> None:
        """Sistemi durdur."""
        if not self._running:
            return
        
        self._running = False
        self.state.status = "stopped"
        
        # Cancel tasks
        for task in self._tasks:
            task.cancel()
        
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        
        # Save state
        self._save_state()
        
        self._log_event("STOP", "System stopped")
    
    def analyze_symbol(self, symbol: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Sembol analizi yap.
        
        Args:
            symbol: Sembol adi
            market_data: Piyasa verileri
        
        Returns:
            Analysis result with signal or None
        """
        self._log_event("ANALYSIS_START", f"Analyzing {symbol}", market_data)
        
        # Check system health
        if not self._check_system_health():
            self._log_event("ANALYSIS_BLOCKED", "System health check failed")
            return None
        
        # Get optimal strategy
        optimal_strategy = self._strategies.get('optimal_profit')
        if not optimal_strategy:
            return None
        
        # Analyze
        signal = optimal_strategy.analyze(symbol, market_data)
        
        if signal:
            self._log_event("SIGNAL_GENERATED", f"{symbol} {signal.direction}", {
                'entry': signal.entry_price,
                'stop_loss': signal.stop_loss,
                'take_profit': signal.take_profit,
                'position_size': signal.position_size_pct,
                'confidence': signal.confidence
            })
            
            return {
                'symbol': symbol,
                'signal': 'BUY' if signal.direction == 'LONG' else 'SELL',
                'entry_price': signal.entry_price,
                'stop_loss': signal.stop_loss,
                'take_profit': signal.take_profit,
                'position_size_pct': signal.position_size_pct,
                'confidence': signal.confidence,
                'regime': signal.regime.value,
                'reasoning': signal.reasoning
            }
        else:
            self._log_event("NO_SIGNAL", f"No signal for {symbol}")
            return None
    
    def record_trade(self, symbol: str, pnl: float, reasoning: str, 
                    features: Dict[str, Any]) -> None:
        """
        Trade kaydet.
        
        Args:
            symbol: Sembol
            pnl: Kar/Zarar
            reasoning: Trade aciklamasi
            features: Ozellikler
        """
        self._performance_history.append({
            'symbol': symbol,
            'pnl': pnl,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'reasoning': reasoning,
            'features': features
        })
        
        # Update optimal strategy
        optimal_strategy = self._strategies.get('optimal_profit')
        if optimal_strategy:
            optimal_strategy.record_trade_result(symbol, pnl, reasoning, features)
        
        self._log_event("TRADE_RECORDED", f"{symbol} PnL: {pnl}", {
            'pnl': pnl,
            'reasoning': reasoning
        })
        
        # Save state
        self._save_state()
    
    def get_status(self) -> Dict[str, Any]:
        """Sistem durumu al."""
        self._update_system_state()
        
        return {
            'status': self.state.status,
            'regime': self.state.regime,
            'mode': self.state.mode,
            'health_score': self.state.health_score,
            'active_trades': self.state.active_trades,
            'daily_pnl': self.state.daily_pnl,
            'daily_pnl_pct': self.state.daily_pnl_pct,
            'total_pnl': self.state.total_pnl,
            'sharpe_ratio': self.state.sharpe_ratio,
            'max_drawdown': self.state.max_drawdown,
            'win_rate': self.state.win_rate,
            'total_trades': self.state.total_trades,
            'active_features': self.state.active_features,
            'errors': self.state.errors[-10:],  # Last 10 errors
            'last_update': self.state.last_update.isoformat()
        }
    
    def get_event_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Olay kayitlarini al."""
        return self._event_log[-limit:]
    
    def emergency_stop(self) -> None:
        """Acil durum durdurmasi."""
        self._log_event("EMERGENCY_STOP", "Emergency stop triggered")
        
        # Close all positions
        execution_engine = self._modules.get('execution_engine')
        if execution_engine and hasattr(execution_engine, 'close_all_positions'):
            execution_engine.close_all_positions()
        
        # Stop system (synchronous version for non-async context)
        self._running = False
        self.state.status = "emergency_stopped"
        self.state.errors.append("Emergency stop triggered")
        
        # Save state
        self._save_state()


# Factory function
def create_master_orchestrator(config: OrchestratorConfig = None) -> MasterOrchestrator:
    """Master orchestrator factory."""
    return MasterOrchestrator(config=config)

