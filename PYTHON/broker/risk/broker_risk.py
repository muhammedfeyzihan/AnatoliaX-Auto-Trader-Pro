"""
risk/broker_risk.py — Araci kuruma ozel risk sarimi
"""
from broker.core.broker_interface import BrokerInterface
from broker.risk.pre_trade_check import PreTradeRiskChecker


class BrokerRiskWrapper:
    """
    Herhangi bir BrokerInterface uzerine on-ticaret risk sarmalayıcı.

    Kullanim:
        safe_broker = BrokerRiskWrapper(broker, PreTradeRiskChecker())
        report = await safe_broker.place_order(order)
    """

    def __init__(self, broker: BrokerInterface, checker: PreTradeRiskChecker):
        self._broker = broker
        self._checker = checker

    async def place_order(self, order):
        # Pozisyon ve PnL degerlerini broker'dan al (yer tutucu)
        result = self._checker.check(order, current_position=0, portfolio_value=1, daily_pnl=0)
        if not result.allowed:
            from broker.core.broker_interface import ExecutionReport, OrderStatus
            return ExecutionReport(
                order_id="RISK-REJECT",
                status=OrderStatus.REJECTED,
                filled_qty=0,
                avg_price=0,
                commission=0,
                timestamp="2026-05-26T12:00:00Z",
            )
        return await self._broker.place_order(order)
