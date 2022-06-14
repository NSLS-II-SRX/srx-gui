import argparse
import os

from bluesky_widgets.qt import gui_qt
from nslsii import _read_bluesky_kafka_config_file

from .viewer import Viewer
from .settings import SETTINGS


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
