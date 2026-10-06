import os
import subprocess
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"

PROBE = """
import core.broker.kafka as kafka

producer = kafka.broker.config.producer
print(type(kafka.broker).__name__, type(producer).__name__)
"""

PLAINTEXT: dict[str, str] = {}
SASL_PLAINTEXT = {
    "KAFKA_SECURITY_PROTOCOL": "SASL_PLAINTEXT",
    "KAFKA_SASL_USERNAME": "bot",
    "KAFKA_SASL_PASSWORD": "secret",
}
SASL_TLS = {
    "KAFKA_SECURITY_PROTOCOL": "SASL_SSL",
    "KAFKA_SASL_USERNAME": "bot",
    "KAFKA_SASL_PASSWORD": "secret",
    "KAFKA_SASL_MECHANISM": "SCRAM-SHA-256",
}


@pytest.mark.parametrize(
    "extra", [PLAINTEXT, SASL_PLAINTEXT, SASL_TLS], ids=["plain", "sasl", "sasl-tls"]
)
def test_the_real_kafka_broker_can_be_built_without_a_connection(
    extra: dict[str, str],
) -> None:
    env = os.environ | {
        "IN_MEMORY_BROKER": "false",
        "MONOLITH": "false",
        "KAFKA_HOST": "localhost",
        "KAFKA_PORT": "9092",
        "PYTHONPATH": str(SRC),
    }

    result = subprocess.run(
        [sys.executable, "-c", PROBE],
        env=env | extra,
        capture_output=True,
        text=True,
        cwd=SRC.parent,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr[-1500:]
    assert "KafkaBroker KafkaRpcProducer" in result.stdout
