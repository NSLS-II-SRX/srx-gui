import bluesky.plan_stubs as bps
from bluesky.plans import count
from bluesky.preprocessors import monitor_during_decorator, run_decorator
from ophyd.sim import det1, det2, motor1, motor2, SynSignal
from ophyd import Signal
import numpy as np


class YPos(Signal):
    ...


y_pos = YPos(name="y_pos")


class SynMonitoredROI(Signal):
    def read_configuration(self):
        return {}

    def describe_configuration(self):
        return {}


roi_name = "Br_ka1"

monitored_roi = SynMonitoredROI(name=roi_name)
roi_pv = monitored_roi
roi_pv.put([])


def scan_and_fly_base(detectors, xstart, xstop, xnum, ystart, ystop, ynum, dwell, *, md=None, snake=False):
    """
    Starting the plan: RE(scan_and_fly_base([det1], 0, 1, 15, 0, 2, 5, 0.1, snake=False))
    """

    # Set metadata
    md = md or {}

    # Check for negative number of points
    if xnum < 1 or ynum < 1:
        raise ValueError("Number of points must be positive!")

    # Scan metadata
    md.setdefault("scan", {})
    md["scan"]["type"] = "XRF_FLY"
    md["scan"]["scan_input"] = [xstart, xstop, xnum, ystart, ystop, ynum, dwell]
    md["scan"]["snake"] = snake
    md["scan"]["shape"] = (xnum, ynum)

    roi_pv.put([])

    def fly_each_step(xnum, n_row, dwell):
        data = list(range(1, xnum + 1))
        data = [_ + n_row * 0.1 for _ in data]
        if snake and (n_row % 2):  # Reverse rows with odd numbers
            data.reverse()
        pts_aver = 9.3
        for n in range(0, int(xnum / pts_aver) + 1):
            monitored_roi.put(np.array(data[: int(n * pts_aver)]))
            # monitored_roi.put([1, 2])
            yield from bps.sleep(dwell * pts_aver)
        monitored_roi.put(np.array(data))
        # monitored_roi.put([1, 2])

    # @monitor_during_decorator([roi_pv])
    @ts_monitor_during_decorator([roi_pv])
    @run_decorator(md=md)
    def plan(xnum, ynum, dwell):
        for n_row in range(ynum):
            yield from bps.checkpoint()

            # Create the 'primary' stream with some data
            yield from bps.create()
            y_pos.put(n_row)
            yield from bps.read(y_pos)

            yield from fly_each_step(xnum=xnum, n_row=n_row, dwell=dwell)

            yield from bps.save()

    yield from plan(xnum=xnum, ynum=ynum, dwell=dwell)