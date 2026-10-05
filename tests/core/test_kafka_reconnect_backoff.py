from core.broker.kafka import MAX_RECONNECT_INTERVAL, next_reconnect_interval


def test_interval_doubles_until_the_cap() -> None:
    assert next_reconnect_interval(0.8) == 1.6
    assert next_reconnect_interval(8) == 16


def test_interval_never_exceeds_the_cap() -> None:
    assert next_reconnect_interval(MAX_RECONNECT_INTERVAL) == MAX_RECONNECT_INTERVAL
    assert next_reconnect_interval(10**9) == MAX_RECONNECT_INTERVAL
