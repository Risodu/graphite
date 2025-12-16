#!/usr/bin/python3
import threading
import time
import sys
from queue import Queue

from graphite.plotview import PlotView
from graphite.model import Model

class Controller:
    "The main control of the application"
    def __init__(self):
        self.model = Model()

        self.plotView = PlotView(self.model)

        self.keybinds = [
            ('+', 'Zoom plot in', lambda: self.model.zoom(0.8)),
            ('-', 'Zoom plot out', lambda: self.model.zoom(1.25)),
            ('Right', 'Shift plot Right', lambda: self.model.xrange.relshift(0.2)),
            ('Left', 'Shift plot Left', lambda: self.model.xrange.relshift(-0.2)),
            ('Up', 'Shift plot Up', lambda: self.model.yrange.relshift(0.2)),
            ('Down', 'Shift plot Down', lambda: self.model.yrange.relshift(-0.2)),
            ('Ctrl+l', 'Shift plot Right', lambda: self.model.xrange.relshift(0.2)),
            ('Ctrl+h', 'Shift plot Left', lambda: self.model.xrange.relshift(-0.2)),
            ('Ctrl+k', 'Shift plot Up', lambda: self.model.yrange.relshift(0.2)),
            ('Ctrl+j', 'Shift plot Down', lambda: self.model.yrange.relshift(-0.2)),
        ]

        self.commands = [
            (':q', 'Quit the application', lambda: self.plotView.root.quit()),
            (':e', 'Export the plot', lambda name = None: self.plotView.export(name))
        ]

        self.keymaps = {}
        for key, desc, act in self.keybinds:
            self.keymaps[key] = act

        self.cmds = {}
        for key, desc, act in self.commands:
            self.cmds[key] = act

        self.input_queue: Queue[str] = Queue()
        threading.Thread(target=self.read_stdin, daemon=True).start()
        self.poll_queue()

        self.plotView.root.bind("<Key>", self.handleInput)
        self.plotView.root.mainloop()

    def handleInput(self, event) -> None:
        keysym: str = event.keysym
        keychar: str = event.char
        s = event.state

        # Manual way to get the modifiers
        ctrl  = (s & 0x4) != 0
        alt   = (s & 0x8) != 0 or (s & 0x80) != 0
        shift = (s & 0x1) != 0

        # Merge it into an output
        if alt:   keysym = 'Alt+' + keysym
        if shift: keysym = 'Shift+' + keysym
        if ctrl:  keysym = 'Ctrl+' + keysym

        # if len(keychar) == 1 and len(keysym) <= 2 and keychar.islower():
        #     keysym = keysym.lower()

        # self.model.code = [f'{k}: {repr(v)}' for k, v in event.__dict__.items()]

        self.action = self.keymaps.get(keysym, None)

        if self.action is None:
            self.action = self.keymaps.get(keychar, None)

        if self.action is not None:
            self.action()

        self.refresh()

    def read_stdin(self):
        for line in sys.stdin:
            self.input_queue.put(line.rstrip())

    def poll_queue(self):
        refresh = not self.input_queue.empty()
        while not self.input_queue.empty():
            self.model.flatCode = self.input_queue.get().replace('<nl>', '\n')
        if refresh:
            self.refresh()
        self.plotView.root.after(10, self.poll_queue)

    def runCommand(self, cmd: str):
        cmd, *args = cmd.split()
        if cmd not in self.cmds:
            m = f'Unknown command: "{cmd}"'
        else:
            m = self.cmds[cmd](*args) or ''

    def refresh(self):
        modelTime.append(timed(self.model.compile))
        plotTime.append(timed(self.plotView.draw))

modelTime = []
plotTime = []
consoleTime = []

def timed(f):
    t = time.time()
    f()
    return time.time() - t

def mainloop() -> None:
    try:
        Controller()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    mainloop()

