import pytest
from infrastructure.messaging_backbone import ExactlyOnceMessagingBackbone, Message


@pytest.fixture
def bus(tmp_path):
    db = str(tmp_path / "idempotency.db")
    return ExactlyOnceMessagingBackbone(db_path=db)


def test_publish_idempotency(bus):
    assert bus.publish("test", {"a": 1}, idempotency_key="key1") is True
    assert bus.publish("test", {"a": 1}, idempotency_key="key1") is False


def test_publish_no_idempotency(bus):
    assert bus.publish("test", {"a": 1}) is True


def test_subscriber_receive(bus):
    received = []
    bus.subscribe("test", lambda msg: received.append(msg))
    bus.publish("test", {"a": 1})
    assert len(received) == 1
    assert received[0].payload == {"a": 1}
