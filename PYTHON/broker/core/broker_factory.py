"""
core/broker_factory.py — Yapilandirmaya dayali broker fabrikasi
"""
from typing import Dict, Type

from broker.core.broker_interface import BrokerInterface


class BrokerFactory:
    """
    Yapilandirmaya dayali broker fabrikasi.

    Kullanim:
        broker = BrokerFactory.create({"broker": "matriks", "username": "..."})
    """

    _registry: Dict[str, Type[BrokerInterface]] = {}

    @classmethod
    def register(cls, name: str, broker_class: Type[BrokerInterface]) -> None:
        cls._registry[name.lower()] = broker_class

    @classmethod
    def create(cls, config: dict) -> BrokerInterface:
        name = config.get("broker", "mock").lower()
        broker_class = cls._registry.get(name)
        if not broker_class:
            raise ValueError(f"Bilinmeyen broker: {name}")
        return broker_class(**{k: v for k, v in config.items() if k != "broker"})
