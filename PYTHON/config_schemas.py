"""
config_schemas.py — Pydantic-validated configuration schemas for all AnatoliaX modules.
K254: All configuration must be validated at startup via Pydantic.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, validator


class QueuePositionConfig(BaseModel):
    max_threshold: float = Field(0.8, ge=0.0, le=1.0)
    decay_rate: float = Field(0.1, ge=0.0)


class HiddenLiquidityConfig(BaseModel):
    imbalance_threshold: float = Field(0.7, ge=0.0, le=1.0)


class SmartSlicerConfig(BaseModel):
    default_slices: int = Field(10, ge=1, le=1000)
    twap_enabled: bool = True
    vwap_enabled: bool = True
    pov_enabled: bool = True
    participation_rate: float = Field(0.1, ge=0.0, le=1.0)


class ExpectedSlippageConfig(BaseModel):
    alpha1: float = Field(0.5, ge=0.0)
    alpha2: float = Field(0.3, ge=0.0)
    alpha3: float = Field(0.2, ge=0.0)


class ToxicityRouterConfig(BaseModel):
    vpin_threshold: float = Field(0.7, ge=0.0, le=1.0)
    expected_slippage: ExpectedSlippageConfig = Field(default_factory=ExpectedSlippageConfig)


class AdverseSelectionConfig(BaseModel):
    realized_spread_window_min: int = Field(5, ge=1)
    liquidity_fade_window_min: int = Field(1, ge=1)


class MicrostructureConfig(BaseModel):
    queue_position: QueuePositionConfig = Field(default_factory=QueuePositionConfig)
    hidden_liquidity: HiddenLiquidityConfig = Field(default_factory=HiddenLiquidityConfig)
    smart_slicer: SmartSlicerConfig = Field(default_factory=SmartSlicerConfig)
    toxicity_router: ToxicityRouterConfig = Field(default_factory=ToxicityRouterConfig)
    adverse_selection: AdverseSelectionConfig = Field(default_factory=AdverseSelectionConfig)


class FormalVerificationConfig(BaseModel):
    max_drawdown_limit: float = Field(0.05, ge=0.0, le=1.0)
    max_position_limit: float = Field(10.0, ge=1.0)
    max_daily_loss_limit: float = Field(0.03, ge=0.0, le=1.0)


class PortfolioIntelligenceConfig(BaseModel):
    lambda_risk: float = Field(0.5, ge=0.0, le=1.0)
    rebalance_frequency_hours: int = Field(4, ge=1, le=168)
    max_sector_exposure: float = Field(0.20, ge=0.0, le=1.0)
    max_total_exposure: float = Field(0.10, ge=0.0, le=1.0)


class FactorExposureConfig(BaseModel):
    window: int = Field(60, ge=10)
    factors: List[str] = Field(default_factory=lambda: [
        "market_beta", "sector_momentum", "volatility_factor",
        "momentum_factor", "macro_rates", "macro_fx", "macro_commodities",
    ])


class DynamicHedgingConfig(BaseModel):
    beta_threshold: float = Field(0.1, ge=0.0)
    delta_threshold: float = Field(500.0, ge=0.0)
    hedge_execution_spread_multiplier: float = Field(0.5, ge=0.0)


class AlphaDecayConfig(BaseModel):
    sharpe_threshold: float = Field(0.5)
    win_rate_threshold: float = Field(40.0)
    profit_factor_threshold: float = Field(1.0)
    max_consecutive_losses: int = Field(5, ge=1)
    cooldown_hours: float = Field(24.0, ge=0.0)


class RiskConfig(BaseModel):
    formal_verification: FormalVerificationConfig = Field(default_factory=FormalVerificationConfig)
    portfolio_intelligence: PortfolioIntelligenceConfig = Field(default_factory=PortfolioIntelligenceConfig)
    factor_exposure: FactorExposureConfig = Field(default_factory=FactorExposureConfig)
    dynamic_hedging: DynamicHedgingConfig = Field(default_factory=DynamicHedgingConfig)
    alpha_decay: AlphaDecayConfig = Field(default_factory=AlphaDecayConfig)


class MessagingConfig(BaseModel):
    max_retries: int = Field(3, ge=0, le=10)
    base_backoff_sec: float = Field(1.0, ge=0.0)
    kafka_replication_factor: int = Field(3, ge=1, le=7)
    redis_retention_hours: int = Field(24, ge=1)
    nats_timeout_sec: int = Field(5, ge=1)


class ObservabilityConfig(BaseModel):
    latency_buckets_ms: List[int] = Field(default_factory=lambda: [1, 5, 10, 50, 100, 500, 1000])
    trace_sample_rate: float = Field(1.0, ge=0.0, le=1.0)
    prometheus_port: int = Field(9090, ge=1024, le=65535)
    jaeger_port: int = Field(16686, ge=1024, le=65535)


class IncidentResponseConfig(BaseModel):
    auto_heal: bool = True
    scale_factor: int = Field(2, ge=1)
    memory_threshold_pct: float = Field(80.0, ge=0.0, le=100.0)
    kafka_lag_threshold: int = Field(1000, ge=0)


class HardwareOptimizationConfig(BaseModel):
    pin_cpu: bool = True
    numa_local: bool = True
    hot_path_target_ns: int = Field(10000, ge=100)
    lock_free_queue: bool = True


class ClusterOrchestrationConfig(BaseModel):
    checkpoint_interval_sec: float = Field(5.0, ge=0.1)
    hpa_cpu_threshold: float = Field(70.0, ge=0.0, le=100.0)
    hpa_latency_p99_threshold_ms: float = Field(100.0, ge=0.0)
    hpa_queue_depth_threshold: int = Field(1000, ge=0)
    rolling_stages: List[float] = Field(default_factory=lambda: [0.1, 0.5, 1.0])

    @validator("rolling_stages")
    def check_rolling_stages(cls, v):
        if len(v) < 1 or v[-1] != 1.0:
            raise ValueError("rolling_stages must end with 1.0")
        return v


class InfrastructureConfig(BaseModel):
    messaging: MessagingConfig = Field(default_factory=MessagingConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    incident_response: IncidentResponseConfig = Field(default_factory=IncidentResponseConfig)
    hardware_optimization: HardwareOptimizationConfig = Field(default_factory=HardwareOptimizationConfig)
    cluster_orchestration: ClusterOrchestrationConfig = Field(default_factory=ClusterOrchestrationConfig)


class MifidConfig(BaseModel):
    rts6_enabled: bool = True
    algorithm_testing_documentation: bool = True
    kill_functionality: bool = True
    real_time_monitoring: bool = True


class AuditTrailConfig(BaseModel):
    timestamp_precision: Literal["nanosecond", "microsecond", "millisecond"] = "nanosecond"
    storage_type: Literal["WORM", "standard"] = "WORM"
    retention_days: int = Field(2555, ge=1)


class SurveillanceConfig(BaseModel):
    spoofing_tau_sec: float = Field(2.0, ge=0.0)
    spoofing_size_multiplier: float = Field(3.0, ge=1.0)
    layering_sequence_threshold: int = Field(5, ge=2)
    wash_trading_self_match_prevention: bool = True


class AmlConfig(BaseModel):
    structuring_threshold_usd: float = Field(10000.0, ge=0.0)
    rapid_movement_threshold: int = Field(5, ge=1)
    sar_workflow: bool = True


class BistSpecificConfig(BaseModel):
    vbts_enabled: bool = True
    circuit_breaker_auto_report: bool = True
    short_selling_ban_check: bool = True


class ComplianceConfig(BaseModel):
    mifid_ii: MifidConfig = Field(default_factory=MifidConfig)
    audit_trail: AuditTrailConfig = Field(default_factory=AuditTrailConfig)
    surveillance: SurveillanceConfig = Field(default_factory=SurveillanceConfig)
    aml: AmlConfig = Field(default_factory=AmlConfig)
    bist_specific: BistSpecificConfig = Field(default_factory=BistSpecificConfig)


class RapidsConfig(BaseModel):
    enabled: bool = True
    memory_pool_size_mb: int = Field(4096, ge=256)


class RayConfig(BaseModel):
    enabled: bool = True
    num_workers: int = Field(4, ge=1)
    object_store_memory_mb: int = Field(2048, ge=256)


class PolarsConfig(BaseModel):
    streaming: bool = True
    lazy_evaluation: bool = True


class OnnxConfig(BaseModel):
    gpu_execution_provider: bool = True
    fallback_cpu: bool = True
    inference_target_ms: float = Field(1.0, ge=0.0)


class GpuPipelineConfig(BaseModel):
    use_gpu: bool = True
    fallback_to_cpu: bool = True
    target_feature_refresh_ms: int = Field(100, ge=1)
    batch_size: int = Field(64, ge=1)
    rapids: RapidsConfig = Field(default_factory=RapidsConfig)
    ray: RayConfig = Field(default_factory=RayConfig)
    polars: PolarsConfig = Field(default_factory=PolarsConfig)
    onnx: OnnxConfig = Field(default_factory=OnnxConfig)


class LatencyConfig(BaseModel):
    mu: float = 0.0
    sigma: float = Field(0.5, ge=0.0)


class SpreadStressConfig(BaseModel):
    beta: float = Field(2.0, ge=0.0)


class SlippageConfig(BaseModel):
    alpha1: float = Field(0.5, ge=0.0)
    alpha2: float = Field(0.3, ge=0.0)
    alpha3: float = Field(0.2, ge=0.0)


class QueueDecayConfig(BaseModel):
    lambda_: float = Field(0.1, ge=0.0)
    noise_std: float = Field(0.05, ge=0.0)


class LiquidityCollapseSimConfig(BaseModel):
    depth_threshold: float = Field(0.3, ge=0.0)
    imbalance_threshold: float = Field(-0.7, le=0.0)


class ValidationConfig(BaseModel):
    epsilon_ratio: float = Field(0.1, ge=0.0, le=1.0)
    target_valid_pct: float = Field(95.0, ge=0.0, le=100.0)


class TickSimulatorConfig(BaseModel):
    latency: LatencyConfig = Field(default_factory=LatencyConfig)
    spread_stress: SpreadStressConfig = Field(default_factory=SpreadStressConfig)
    slippage: SlippageConfig = Field(default_factory=SlippageConfig)
    queue_decay: QueueDecayConfig = Field(default_factory=QueueDecayConfig)
    liquidity_collapse: LiquidityCollapseSimConfig = Field(default_factory=LiquidityCollapseSimConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)


class AdversarialConfig(BaseModel):
    episodes: int = Field(100, ge=1)
    win_rate_threshold: float = Field(0.60, ge=0.0, le=1.0)
    agents: List[str] = Field(default_factory=lambda: ["panic", "spoofing", "institutional_predator", "liquidity_trap"])


class TimeFrontierConfig(BaseModel):
    clock_increment_ns: int = Field(1, ge=0)
    max_look_ahead_ticks: int = Field(0, ge=0)


class SimulationConfig(BaseModel):
    tick_simulator: TickSimulatorConfig = Field(default_factory=TickSimulatorConfig)
    adversarial: AdversarialConfig = Field(default_factory=AdversarialConfig)
    time_frontier: TimeFrontierConfig = Field(default_factory=TimeFrontierConfig)


class AnatoliaXConfig(BaseModel):
    """Root configuration validated at system startup."""
    microstructure: MicrostructureConfig = Field(default_factory=MicrostructureConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    infrastructure: InfrastructureConfig = Field(default_factory=InfrastructureConfig)
    compliance: ComplianceConfig = Field(default_factory=ComplianceConfig)
    gpu: GpuPipelineConfig = Field(default_factory=GpuPipelineConfig)
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)
