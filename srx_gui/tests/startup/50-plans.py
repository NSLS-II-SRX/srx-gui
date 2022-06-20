import bluesky.plan_stubs as bps
from bluesky.plan_stubs import mv
from bluesky.plans import count
from bluesky.preprocessors import monitor_during_decorator, run_decorator, subs_decorator
import ophyd
from ophyd import Signal, Device, Component as Cpt
from ophyd.sim import det1, det2, motor1, motor2, SynSignal
import numpy as np


class SRXNanoStage(Device):
    x = Cpt(ophyd.sim.SynAxis, name="x", labels={"motors"})
    y = Cpt(ophyd.sim.SynAxis, name="y", labels={"motors"})
    z = Cpt(ophyd.sim.SynAxis, name="z", labels={"motors"})
    xx = Cpt(ophyd.sim.SynAxis, name="xx", labels={"motors"})
    yy = Cpt(ophyd.sim.SynAxis, name="yy", labels={"motors"})
    zz = Cpt(ophyd.sim.SynAxis, name="zy", labels={"motors"})
    th = Cpt(ophyd.sim.SynAxis, name="th", labels={"motors"})

    def set(self, x, y, z, xx, yy, zz, th):
        """Makes the device Movable"""
        self.x.set(x)
        self.y.set(y)
        self.z.set(z)
        self.xx.set(xx)
        self.yy.set(yy)
        self.zz.set(zz)
        self.th.set(th)


nano_stage = SRXNanoStage(name="nano_stage")

sx = Signal(name="sx")


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


def scan_and_fly_base(
    detectors,
    xstart,
    xstop,
    xnum,
    ystart,
    ystop,
    ynum,
    dwell,
    *,
    md=None,
    snake=False,
    plot=False,
    shutter=True,
):
    """
    Starting the plan: RE(scan_and_fly_base([det1], 0, 1, 15, 0, 2, 5, 0.1, snake=False))
    """

    # Set metadata
    md = md or {}

    # Check for negative number of points
    if xnum < 1 or ynum < 1:
        raise ValueError("Number of points must be positive!")

    xmotor = sx

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
            v = np.array(data[: int(n * pts_aver)])
            monitored_roi.put(v)
            # yield from bps.abs_set(monitored_roi, v, wait=True)
            yield from bps.sleep(dwell * pts_aver)
        monitored_roi.put(np.array(data))

    if plot:
        if ynum == 1:
            livepopup = [
                # SRX1DFlyerPlot(
                SRX1DTSFlyerPlot(
                    roi_pv.name, xstart=xstart, xstep=(xstop - xstart) / (xnum - 1), xlabel=xmotor.name
                )
            ]
        else:
            livepopup = [
                # LiveGrid(
                TSLiveGrid(
                    (ynum, xnum),
                    roi_pv.name,
                    extent=(xstart, xstop, ystart, ystop),
                    x_positive="right",
                    y_positive="down",
                )
            ]
    else:
        livepopup = []

    @subs_decorator(livepopup)
    # @monitor_during_decorator([roi_pv])
    @ts_monitor_during_decorator([roi_pv])
    @run_decorator(md=md)
    def plan(xnum, ynum, dwell):
        for n_row in range(ynum):
            yield from bps.checkpoint()

            # Create the 'primary' stream with some data
            yield from bps.create()
            # y_pos.put(n_row)
            yield from bps.abs_set(y_pos, n_row, wait=True)
            yield from bps.read(y_pos)

            yield from fly_each_step(xnum=xnum, n_row=n_row, dwell=dwell)

            yield from bps.save()

    yield from plan(xnum=xnum, ynum=ynum, dwell=dwell)


def nano_scan_and_fly(*args, extra_dets=None, center=True, **kwargs):
    """
    Emulation of ``nano_scan_and_fly`` plan.
    """
    dets = [det1]
    if extra_dets:
        dets.extend(extra_dets)
    yield from scan_and_fly_base(dets, *args, **kwargs)


def check_shutters(check, status):
    """
    Emulation of ``check_shutters`` plan.
    """
    if not isinstance(check, bool):
        raise TypeError("Incorrect type of 'check' parameter: {type(check)}")

    if status == "Open":
        print("Opening D-hutch shutter...")
        yield from bps.sleep(1)
    elif status == "Close":
        print("Closing D-hutch shutter...")
        yield from bps.sleep(1)
    else:
        raise ValueError(f"Incorrect value of 'status': {status}")
