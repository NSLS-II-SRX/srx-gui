# Before running plans:
# - Install Mongo
# - Copy databroker config file 'srx-gui/tests/config/srx.yml' to '~/.config/databroker/srx.yml'
# - Create the directory '~/.config/bluesky/persistent_dict'
# - Copy 'srx-gui/tests/config/kafka.yml' to '~/.config/bluesky/kafka.yml'
# - set valid path to Bluesky Kafka config:
#   BLUESKY_KAFKA_CONFIG_PATH=~/.config/bluesky/kafka.yml
# - Start Kafka: set 'srx-gui/tests/config' as a current directory and run
#   sudo docker-compose -f bitnami-kafka-docker-compose.yml up
# - Start GUI:
#   srx-gui --kafka-servers localhost:9092 --kafka-topics srx.bluesky.runengine.documents

import os
from bluesky import RunEngine

RE = RunEngine()

from databroker import Broker

db = Broker.named("srx")
RE.subscribe(db.insert)

from bluesky import SupplementalData

sd = SupplementalData()
RE.preprocessors.append(sd)

from bluesky.callbacks.best_effort import BestEffortCallback

bec = BestEffortCallback()
bec.disable_plots()
RE.subscribe(bec)

from bluesky.utils import PersistentDict
from pathlib import Path

runengine_metadata_dir = Path(os.path.expanduser("~/.config/bluesky/persistent_dict"))
RE.md = PersistentDict(runengine_metadata_dir)

from bluesky_kafka.utils import create_topics, list_topics

bootstrap_servers = "localhost:9092"
topic = "srx.bluesky.runengine.documents"
if topic not in list_topics(bootstrap_servers):
    print(f"Creating Kafka topic: {topic!r}")
    create_topics(bootstrap_servers, [topic])
else:
    print(f"Kafka topic {topic!r} already exists")

from nslsii import configure_kafka_publisher

kafka_config_path = "~/.config/bluesky/kafka.yml"
kafka_config_path = os.path.expanduser(kafka_config_path)
configure_kafka_publisher(RE, "SRX", override_config_path=kafka_config_path)
