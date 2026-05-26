import pytest
from agents.research_agents import AutonomousResearchAgent


def test_generate_hypothesis_insufficient_data():
    agent = AutonomousResearchAgent()
    hyp = agent.generate_hypothesis(data=[1.0, 2.0], symbol="THYAO", feature="close")
    assert hyp is None


def test_generate_hypothesis_detects_anomaly():
    agent = AutonomousResearchAgent()
    data = [1.0] * 20 + [100.0]  # clear outlier
    hyp = agent.generate_hypothesis(data=data, symbol="THYAO", feature="close")
    assert hyp is not None
    assert hyp.symbol == "THYAO"
    assert hyp.anomaly_score > 2.5


def test_design_experiment():
    agent = AutonomousResearchAgent()
    data = [1.0] * 20 + [100.0]
    hyp = agent.generate_hypothesis(data=data, symbol="THYAO", feature="close")
    assert hyp is not None
    config = agent.design_experiment(hyp, data_window=252)
    assert config["hypothesis_id"] == hyp.id
    assert "parameters" in config


def test_run_backtest():
    agent = AutonomousResearchAgent()
    returns = [0.01] * 50 + [-0.01] * 50
    result = agent.run_backtest({"hypothesis_id": "HYP-1"}, returns)
    assert "sharpe" in result
    assert "max_dd" in result
    assert result["trades"] == 100


def test_validate():
    agent = AutonomousResearchAgent(sharpe_threshold=1.0, max_dd_threshold=0.15)
    assert agent.validate({"sharpe": 1.5, "max_dd": 0.05}) is True
    assert agent.validate({"sharpe": 0.5, "max_dd": 0.05}) is False
    assert agent.validate({"sharpe": 1.5, "max_dd": 0.20}) is False


def test_pipeline_no_anomaly():
    agent = AutonomousResearchAgent()
    data = [1.0] * 30
    result = agent.pipeline(data, symbol="THYAO", feature="close", returns=data)
    assert result is None
