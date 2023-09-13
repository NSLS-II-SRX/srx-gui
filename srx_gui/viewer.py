import os
import copy
import pprint
import uuid

from bluesky_widgets.models.run_engine_client import RunEngineClient
from bluesky_widgets.qt import Window

# from bluesky_widgets.models.plot_specs import Axes, Figure
# from bluesky_widgets.models.plot_builders import Lines
# from bluesky_widgets.models.auto_plot_builders import AutoPlotter

from .widgets import QtViewer

# from .models import SearchWithButton
from .settings import SETTINGS

from .plots import AutoSRXPlot


class ViewerModel:
    """
    This encapsulates on the models in the application.
    """

    def __init__(self):
        # self.search = SearchWithButton(SETTINGS.catalog, columns=SETTINGS.columns)
        # auto_plot_builder for live plotting
        self.live_auto_plot_builder = AutoSRXPlot()
        # auto_plot_builder for databroker plotting
        self.databroker_auto_plot_builder = AutoSRXPlot()

        self.run_engine = RunEngineClient(
            zmq_control_addr=SETTINGS.zmq_control_addr,
            zmq_info_addr=SETTINGS.zmq_info_addr,
        )


class Viewer(ViewerModel):
    """
    This extends the model by attaching a Qt Window as its view.

    This object is meant to be exposed to the user in an interactive console.
    """

    def __init__(self, *, show=True, title="Demo App"):
        # TODO Where does title thread through?
        super().__init__()
        for source in SETTINGS.subscribe_to:
            if source["protocol"] == "zmq":
                from bluesky_widgets.qt.zmq_dispatcher import RemoteDispatcher
                from bluesky_widgets.utils.streaming import stream_documents_into_runs

                zmq_addr = source["zmq_addr"]

                dispatcher = RemoteDispatcher(zmq_addr)
                dispatcher.subscribe(stream_documents_into_runs(self.live_auto_plot_builder.add_run))
                dispatcher.start()

            elif source["protocol"] == "kafka":
                from bluesky_kafka import RemoteDispatcher
                from bluesky_widgets.utils.streaming import stream_documents_into_runs
                from qtpy.QtCore import QThread

                bootstrap_servers = source["servers"]
                topics = source["topics"]
                consumer_config = source["config"]
                consumer_config.update({"auto.commit.interval.ms": 100, "auto.offset.reset": "latest"})

                # We do not want to print passwords
                consumer_config_copy = copy.deepcopy(consumer_config)
                for k in consumer_config_copy.keys():
                    if "password" in k:
                        consumer_config_copy[k] = "< ... >"
                print("Subscribing to Kafka ...")
                print(f"Bootstrap servers: {bootstrap_servers}")
                print(f"Topics: {topics}")
                print(f"Consumer configuration: {pprint.pformat(consumer_config_copy)}")

                self.dispatcher = RemoteDispatcher(
                    topics=topics,
                    bootstrap_servers=bootstrap_servers,
                    group_id="widgets_test_" + str(uuid.uuid4()).split("-")[-1],  # Random group name
                    consumer_config=consumer_config,
                )

                self.dispatcher.subscribe(stream_documents_into_runs(self.live_auto_plot_builder.add_run))

                class DispatcherStart(QThread):
                    def __init__(self, dispatcher):
                        super().__init__()
                        self._dispatcher = dispatcher

                    def run(self):
                        self._dispatcher.start()

                self.dispatcher_thread = DispatcherStart(self.dispatcher)
                self.dispatcher_thread.start()

            else:
                print(f"Unknown protocol: {source['protocol']}")

        # Customize Run Engine model for BMM:
        #   - name of the module that contains custom code modules
        #     (conversion of spreadsheets to sequences of plans)
        # self.run_engine.qserver_custom_module_name = "bluesky-httpserver-bmm"
        #   - list of names of spreadsheet types
        # self.run_engine.plan_spreadsheet_data_types = ["wheel_xafs"]

        widget = QtViewer(self)
        self._window = Window(widget, show=show)

    @property
    def window(self):
        return self._window

    def show(self):
        """Resize, show, and raise the window."""
        self._window.show()

    def close(self):
        """Close the window."""
        self._window.close()
