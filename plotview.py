from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import matplotlib.colors as clrs
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import MultipleLocator
import tkinter as tk
import numpy as np
import matplotlib.style as mplstyle
mplstyle.use('fast')

from graphite.model import Model, Interval

def multabs(x):
    if x >= 1: return x
    return 1 / x

MAJOR_TICKS = 15
colors = plt.get_cmap('tab10').colors # type: ignore

class ResettableLine(Line2D):
    changes: dict
    @classmethod
    def fromBase(cls, obj: Line2D) -> "ResettableLine":
        obj.__class__ = cls
        obj.changes = {} # type: ignore
        return obj # type: ignore

    def __setitem__(self, k: str, v):
        if k not in self.changes:
            self.changes[k] = getattr(self, 'get_' + k)()
        getattr(self, 'set_' + k)(v)

    def reset(self):
        for k, v in self.changes.items():
            self[k] = v
        self.changes.clear()

class PlotView:
    "Class that manages the view of the plot"
    def __init__(self, model: Model) -> None:
        self.root = tk.Tk()
        self.root.title("Plot + Keyboard in single loop")
        self.model = model
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        # self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.lines: list[ResettableLine] = []

        self.ax.axhline(0, color="black", linewidth=1)
        self.ax.axvline(0, color="black", linewidth=1)
        # Gridlines
        self.ax.grid(which="major", color="gray", linewidth=0.8, alpha=0.7)
        self.ax.grid(which="minor", color="gray", linewidth=0.5, alpha=0.3)

        self.draw()

    def getTickSize(self, span):
        multiplier = 1
        sqrt10 = 3.1622776601683795
        while span / MAJOR_TICKS > sqrt10:
            multiplier *= 10
            span /= 10
        
        while span / MAJOR_TICKS < sqrt10 * 0.1:
            multiplier /= 10
            span *= 10

        return multiplier

    def computeTiks(self, interval: Interval):
        l = interval.len()
        ones = self.getTickSize(l)
        twos = self.getTickSize(l / 2) * 2
        fivs = self.getTickSize(l / 5) * 5

        major = min((ones, twos, fivs), key=lambda x: multabs(l / x))

        minor = major * (0.25 if '2' in str(major) else 0.2)

        return major, minor

    def recomputeTiks(self) -> None:
        # Major ticks every 1, minor ticks every 0.2 (5 per major)
        majx, minx = self.computeTiks(self.model.xrange)
        majy, miny = self.computeTiks(self.model.yrange)
        self.ax.xaxis.set_major_locator(MultipleLocator(majx))
        self.ax.yaxis.set_major_locator(MultipleLocator(majy))
        self.ax.xaxis.set_minor_locator(MultipleLocator(minx))
        self.ax.yaxis.set_minor_locator(MultipleLocator(miny))

    def draw(self) -> None:
        "Executes the model code and draws the plot"
        x = np.linspace(*self.model.xrange, 1000) # type: ignore
        self.ax.set_visible(False)
        # self.ax.clear()
        self.recomputeTiks()
        
        data = self.model.execute(x)
        while len(self.lines) < len(data):
            self.lines += map(ResettableLine.fromBase, self.ax.plot(x, x))

        while len(self.lines) > len(data):
            l = self.lines.pop()
            l.remove()

        for i, line, info in zip(range(len(data)), self.lines, data):
            line.reset()
            points, kws = info
            line.set_visible(True)
            line.set_data(*points)
            line.set_color(colors[i % len(colors)])
            for kw in kws:
                if clrs.is_color_like(kw):
                    line.set_color(kw)
                if clrs.is_color_like('#' + kw):
                    line.set_color('#' + kw)

                if kw == "hide":
                    line.set_visible(False)
                    continue

                if '=' in kw:
                    k, v = kw.split('=')

                    if k == "xlabel":
                        self.ax.set_xlabel(v)
                        continue
                    if k == "ylabel":
                        self.ax.set_ylabel(v)
                        continue

                    try:
                        line[k] = v
                        # FIXME: report errors to user
                    except ValueError:
                        pass
                    except AttributeError:
                        pass


        self.ax.set_xlim(*self.model.xrange)
        self.ax.set_ylim(*self.model.yrange)
        self.ax.set_visible(True)
        self.ax.legend()
        self.canvas.draw()

    def export(self, filename: str | None):
        "Exports the plot"
        if filename is None:
            return "No file specified"
        try:
            plt.savefig(filename, format=filename.split('.')[-1])
            return f'Saved to file `{filename}`'
        except Exception as err:
            return str(err)

