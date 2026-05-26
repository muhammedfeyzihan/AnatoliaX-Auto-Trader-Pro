import pytest
from infrastructure.cluster_orchestration import ClusterOrchestrator, StrategyDeployment


def test_deploy_sets_running():
    orch = ClusterOrchestrator()
    dep = StrategyDeployment(
        name="strat-v1",
        replicas=10,
        cpu_limit="500m",
        memory_limit="1Gi",
        strategy_version="1.0.0",
    )
    orch.deploy(dep)
    assert dep.status == "running"
    assert orch._deployments["strat-v1"] == dep


def test_auto_scale_cpu():
    orch = ClusterOrchestrator()
    dep = StrategyDeployment(
        name="strat-v1",
        replicas=2,
        cpu_limit="500m",
        memory_limit="1Gi",
        strategy_version="1.0.0",
    )
    orch.deploy(dep)
    orch._metrics["strat-v1"] = {"cpu_pct": 80.0, "latency_p99_ms": 50.0, "queue_depth": 10}
    orch.auto_scale("strat-v1")
    assert dep.replicas > 2


def test_checkpoint_and_restore():
    orch = ClusterOrchestrator()
    orch.checkpoint("engine", {"state": "active"})
    restored = orch.restore("engine")
    assert restored == {"state": "active"}


def test_restore_missing():
    orch = ClusterOrchestrator()
    assert orch.restore("missing") is None


def test_elect_leader():
    orch = ClusterOrchestrator()
    assert orch.elect_leader("component_A", "pod_1") is True
    assert orch.elect_leader("component_A", "pod_2") is False
    assert orch.elect_leader("component_A", "pod_1") is True


def test_rolling_update_status():
    orch = ClusterOrchestrator()
    dep = StrategyDeployment(
        name="strat-v1",
        replicas=3,
        cpu_limit="500m",
        memory_limit="1Gi",
        strategy_version="1.0.0",
    )
    orch.deploy(dep)
    status = orch.rolling_update_status()
    assert status["strat-v1"] == "running"
