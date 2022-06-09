from bluesky_widgets.models.auto_plot_builders import AutoPlotter
from bluesky_widgets.models.plot_builders import Lines, Images, RasteredImages
from bluesky_widgets.models.plot_specs import Axes, Figure, Image
from bluesky_widgets.models.utils import run_is_live_and_not_completed

import numpy as np

import pprint

# plan_name
# underlying_plan linescan motor type
# underlying_plan xafs trans/fluorescence/ref

monitored_line = "Br_ka1"
monitored_stream_name = f"{monitored_line}_monitor"


class AutoSRXPlot(AutoPlotter):
    def __init__(self):
        super().__init__()
        self._models = {}
        self._figure_dict = {}

        self.plot_builders.events.removed.connect(self._on_plot_builder_removed)

    def _on_plot_builder_removed(self, event):
        plot_builder = event.item
        for key in list(self._models):
            for line in self._models[key]:
                if line == plot_builder:
                    del self._models[key]

    def add_run(self, run, **kwargs):
        print("Add run .......")  ##
        super().add_run(run, **kwargs)

    def handle_new_stream(self, run, stream_name):
        print(f"Kafka .......... stream_name={stream_name!r}")  ##
        print(f"Run metadata: {run.metadata['start']}")
        print(f"Run is live: {run_is_live_and_not_completed(run)}")
        # print(f"type(run)={type(run)}")
        # print(f"run = {pprint.pformat(list(run.documents(fill='no')))}")
        # print(f"run = {dict(run)}")
        # print(f"run = {run[monitored_stream_name].to_dask().load()}")

        # if stream_name != "primary":
        if stream_name != monitored_stream_name:
            return

        # nx, ny = run._document_cache.start_doc["scan"]["shape"]

        # Find out the plan type.
        plan_name = run.metadata["start"].get("plan_name").split(" ")
        # if len(plan_name) > 1:
        #     plan = plan_name[1]

        # # Skip plan if it is not supported.
        # if plan not in ["xafs", "linescan"]:
        #     return

        # # Gather the rest of the parameters.
        # subtype = plan_name[-1]  # trans, ref, fluorescence, I0, It, Ir
        # element = run.metadata["start"].get("XDI", {}).get("Element", {}).get("symbol", False)
        # fluorescence = f"{element}1+{element}2+{element}3+{element}4" if element else None

        # # Look up what goes on the x-axis.
        # x_lookup = {"linescan": plan_name[2], "xafs": "dcm_energy"}
        # x_axis = x_lookup[plan]

        # # Look up what goes on the y-axis.
        # y_lookup = {
        #     "I0": ["I0"],
        #     "It": ["It/I0"],
        #     "Ir": ["Ir/It"],
        #     "If": [f"({fluorescence})/I0"],
        #     "trans": ["log(I0/It)", "log(It/Ir)", "I0", "It/I0", "Ir/It"],
        #     "fluorescence": [f"({fluorescence})/I0", "log(I0/It)", "log(It/Ir)", "I0", "It/I0", "Ir/It"],
        #     "ref": ["log(It/Ir)", "It/I0", "Ir/It"],
        # }
        # y_axes = y_lookup[subtype]

        x_axis = "index_count"
        y_axes = [monitored_line]

        for y_axis in y_axes:
            title = " ".join(plan_name)
            subtitle = y_axis
            key = f"{title}: {subtitle}"

            append_figure = False
            if key in self._models:
                print(f"Existing figure")
                models = self._models[key]
                figure = self._figure_dict.get(key, None)
                if not figure or figure not in self.figures:
                    figure = Figure((Axes(),), title=key)
                    self._figure_dict[key] = figure
                    append_figure = True
            else:
                print(f"New figure")
                # model, figure = self.single_plot(f"{title}: {subtitle}", x_axis, y_axis)
                model, figure = self.single_image(f"{title}: {subtitle}", field=y_axis)
                # model, figure = self.single_rastered_image(f"{title}: {subtitle}", field=y_axis, shape=[ny, nx])
                models = [model]
                self._models[key] = [model]
                self._figure_dict[key] = figure
                append_figure = True

            for model in models:
                model.add_run(run)
                self.plot_builders.append(model)
                if append_figure:
                    self.figures.append(figure)

        return model, figure

    def calc_x(self, run):  ##
        print(f"'calc_x' called ...")
        print(f"run={list(run.documents(fill='no'))}")
        return [0, 0.5]

    def calc_y(self, run):  ##
        print(f"'calc_y' called ...")
        return [[1], [2]]

    def single_plot(self, title, x, y):
        axes1 = Axes()
        figure = Figure((axes1,), title=title)
        # x, y = self.calc_x, self.calc_y  ##
        model = Lines(
            x=x,
            ys=[y],
            max_runs=10,
            axes=axes1,
            needs_streams=[monitored_stream_name],
        )
        return model, figure

    def calc_field(self, run):  ##
        print(f"'calc_field' called ...")
        print(f"start={run._document_cache.start_doc}")
        nx, ny = run._document_cache.start_doc["scan"]["shape"]
        data = run[monitored_stream_name].to_dask().load()
        print(f"data[monitored_line]={data[monitored_line]}")
        print(f"data[index_count]={data['index_count']}")
        print(f"data[reset_count]={data['reset_count']}")
        img_data = data[monitored_line]
        n_total = nx * ny
        if len(img_data) > n_total:
            img_data = img_data[:n_total]
        else:
            img_data = np.pad(img_data, (0, n_total - len(img_data)), constant_values=np.nan)
        img_data = img_data.reshape([ny, nx])
        return img_data

    def single_image(self, title, field):
        axes1 = Axes()
        figure = Figure((axes1,), title=title)
        field = self.calc_field  ##
        model = Images(
            field,
            max_runs=1,
            axes=axes1,
            needs_streams=[monitored_stream_name],
        )
        # for artist in model.axes.artists:
        #     if isinstance(artist, Image):
        #         artist.style.update({"clim": (-50, 50)})
        return model, figure

    def single_rastered_image(self, title, field, shape):
        axes1 = Axes()
        figure = Figure((axes1,), title=title)
        field = self.calc_field  ##
        model = RasteredImages(field, max_runs=1, axes=axes1, needs_streams=[monitored_stream_name], shape=shape)
        return model, figure
