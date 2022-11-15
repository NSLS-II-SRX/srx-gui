import argparse
import os

from bluesky_widgets.qt import gui_qt
from pathlib import Path

from .viewer import Viewer
from .settings import SETTINGS


def _read_bluesky_kafka_config_file(config_file_path):
    """Read a YAML file of Kafka producer configuration details.

    The file must have three top-level entries as shown:
    ---
        abort_run_on_kafka_exception: true
        bootstrap_servers:
            - kafka1:9092
            - kafka2:9092
        runengine_producer_config:
            acks: 0
            message.timeout.ms: 3000
            compression.codec: snappy

    Parameters
    ----------
    config_file_path: str
        path to the YAML file of Kafka producer configuration details

    Returns
    -------
    dict of configuration details
    """
    import yaml

    # read the Kafka Producer configuration details
    if Path(config_file_path).exists():
        with open(config_file_path) as f:
            bluesky_kafka_config = yaml.safe_load(f)
    else:
        raise FileNotFoundError(config_file_path)

    required_sections = (
        "abort_run_on_kafka_exception",
        "bootstrap_servers",
        # "producer_consumer_security_config",  not required yet
        "runengine_producer_config",
    )
    missing_required_sections = [
        required_section for required_section in required_sections if required_section not in bluesky_kafka_config
    ]

    if missing_required_sections:
        raise Exception(
            f"Bluesky Kafka configuration file '{config_file_path}' is missing required section(s) "
            f"{missing_required_sections}"
        )

    return bluesky_kafka_config


def read_kafka_configuration(kafka_config_path=None):
    """Read a Kafka configuration file and subscribe a Kafka publisher to the RunEngine.

    A configuration file is required. Environment variable BLUESKY_KAFKA_CONFIG_FILE
    will be checked if `configuration_file_path` is not specified. Otherwise the default
    path `/etc/bluesky/kafka.yml` will be read.

    The intention is that the default path is used in production. The environment variable
    allows for modifying a deployed system and the parameter is useful for testing.
    """

    bluesky_kafka_config_path = None

    if kafka_config_path is not None:
        bluesky_kafka_config_path = kafka_config_path
    elif "BLUESKY_KAFKA_CONFIG_PATH" in os.environ:
        bluesky_kafka_config_path = os.environ["BLUESKY_KAFKA_CONFIG_PATH"]
    else:
        bluesky_kafka_config_path = "/etc/bluesky/kafka.yml"

    if not os.path.isfile(bluesky_kafka_config_path):
        return None, {}

    bluesky_kafka_configuration = _read_bluesky_kafka_config_file(bluesky_kafka_config_path)
    # convert the list of bootstrap servers into a comma-delimited string
    #   which is the format required by the confluent python api
    bootstrap_servers = ",".join(bluesky_kafka_configuration["bootstrap_servers"])
    bluesky_kafka_configuration = bluesky_kafka_configuration["runengine_producer_config"]

    return bootstrap_servers, bluesky_kafka_configuration


def main(argv=None):
    print(__doc__)

    parser = argparse.ArgumentParser(description="SRX GUI: acquisition GUI for NSLS-II SRX beamline")
    parser.add_argument("--zmq", help="0MQ address")
    parser.add_argument(
        "--kafka-config-path",
        default=None,
        help="Full path to Kafka configuration file. The default path '/etc/bluesky/kafka.yml'"
        "is used if the parameter is not specified. If there is not configuration file, "
        "then Kafka is configured based on CLI parameters.",
    )
    parser.add_argument(
        "--kafka-servers",
        default=None,
        help="Kafka servers, comma-separated string, e.g. "
        "'kafka1.nsls2.bnl.gov:9092,kafka2.nsls2.bnl.gov:9092,kafka3.nsls2.bnl.gov:9092'. "
        "The list of servers override the list of servers in Kafka config file.",
    )
    parser.add_argument(
        "--kafka-topics", help="Kafka servers, comma-separated string, e.g. bmm.bluesky.runengine.documents"
    )
    parser.add_argument("--catalog", help="Databroker catalog")
    args = parser.parse_args(argv)

    with gui_qt("SRX GUI"):
        if args.catalog:
            import databroker

            SETTINGS.catalog = databroker.catalog[args.catalog]

        # Optional: Receive live streaming data.
        if args.zmq:
            SETTINGS.subscribe_to.append({"protocol": "zmq", "zmq_addr": args.zmq})

        # Use default path if it is not specififed
        kafka_config_path = args.kafka_config_path or None
        if kafka_config_path:
            kafka_config_path = os.path.expanduser(kafka_config_path)
            kafka_config_path = os.path.abspath(kafka_config_path)
        kafka_servers, kafka_config = read_kafka_configuration(kafka_config_path)
        kafka_servers = kafka_servers or args.kafka_servers
        kafka_topics = args.kafka_topics
        kafka_topics = args.kafka_topics.split(",")
        kafka_topics = [_.strip() for _ in kafka_topics]
        kafka_topics = [_ for _ in kafka_topics if _]  # Removes empty strings

        print(f"kafka_servers: {kafka_servers}")
        print(f"kafka_topics: {kafka_topics}")

        if kafka_servers and kafka_topics:
            source = {
                "protocol": "kafka",
                "servers": kafka_servers,
                "topics": kafka_topics,
                "config": kafka_config,
            }
            SETTINGS.subscribe_to.append(source)

        viewer = Viewer()  # noqa: 401


if __name__ == "__main__":
    main()
