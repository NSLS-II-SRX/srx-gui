import argparse

from bluesky_widgets.qt import gui_qt

from .viewer import Viewer
from .settings import SETTINGS


def main(argv=None):
    print(__doc__)

    parser = argparse.ArgumentParser(description="SRX GUI: acquisition GUI for NSLS-II SRX beamline")
    parser.add_argument("--zmq", help="0MQ address")
    parser.add_argument(
        "--kafka-servers",
        help="Kafka servers, comma-separated string, e.g. "
        "kafka1.nsls2.bnl.gov:9092,kafka2.nsls2.bnl.gov:9092,kafka3.nsls2.bnl.gov:9092",
    )
    parser.add_argument(
        "--kafka-topics", help="Kafka servers, comma-separated string, e.g. bmm.bluesky.runengine.documents"
    )
    parser.add_argument("--catalog", help="Databroker catalog")
    parser.add_argument("--monitored-line", required=True, help="Monitored emission line, e.g. Br_ka1")
    args = parser.parse_args(argv)

    with gui_qt("SRX GUI"):
        if args.monitored_line:
            SETTINGS.monitored_line = args.monitored_line
        if args.catalog:
            import databroker

            SETTINGS.catalog = databroker.catalog[args.catalog]

        # Optional: Receive live streaming data.
        if args.zmq:
            SETTINGS.subscribe_to.append({"protocol": "zmq", "zmq_addr": args.zmq})
        if args.kafka_servers and args.kafka_topics:
            kafka_servers = args.kafka_servers
            kafka_topics = args.kafka_topics.split(",")
            kafka_topics = [_.strip() for _ in kafka_topics]
            source = {"protocol": "kafka", "servers": kafka_servers, "topics": kafka_topics}
            SETTINGS.subscribe_to.append(source)

        viewer = Viewer()  # noqa: 401


if __name__ == "__main__":
    main()
