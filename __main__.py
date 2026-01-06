#!/usr/bin/python3
import time
import sys
import optparse
from queue import Queue

from graphite.plotview import PlotView
from graphite.model import Model
from graphite.input_handler import InputHandler, StreamInputHandler, LSPInputHandler

class Controller:
    "The main control of the application"
    def __init__(self, inHandler: type[InputHandler]):
        self.model = Model()
        self.plotView = PlotView(self.model)
        self.input_handler = inHandler(sys.stdin, sys.stdout, self) # type: ignore
        self.poll_input()

        self.keybinds = [
            ('+', 'Zoom plot in', lambda: self.model.zoom(0.8)),
            ('-', 'Zoom plot out', lambda: self.model.zoom(1.25)),
            ('L', 'Zoom x-axis in', lambda: self.model.xrange.zoom(0.8)),
            ('H', 'Zoom x-axis out', lambda: self.model.xrange.zoom(1.25)),
            ('K', 'Zoom y-axis in', lambda: self.model.yrange.zoom(0.8)),
            ('J', 'Zoom y-axis out', lambda: self.model.yrange.zoom(1.25)),
            ('Right', 'Shift plot Right', lambda: self.model.xrange.relshift(0.2)),
            ('Left', 'Shift plot Left', lambda: self.model.xrange.relshift(-0.2)),
            ('Up', 'Shift plot Up', lambda: self.model.yrange.relshift(0.2)),
            ('Down', 'Shift plot Down', lambda: self.model.yrange.relshift(-0.2)),
            ('l', 'Shift plot Right', lambda: self.model.xrange.relshift(0.2)),
            ('h', 'Shift plot Left', lambda: self.model.xrange.relshift(-0.2)),
            ('k', 'Shift plot Up', lambda: self.model.yrange.relshift(0.2)),
            ('j', 'Shift plot Down', lambda: self.model.yrange.relshift(-0.2)),
        ]

        self.commands = [
            ('q', 'Quit the application', lambda: self.plotView.root.quit()),
            ('e', 'Export the plot', lambda name = None: self.plotView.export(name))
        ]

        self.keymaps = {}
        for key, desc, act in self.keybinds:
            self.keymaps[key] = act

        self.cmds = {}
        for key, desc, act in self.commands:
            self.cmds[key] = act

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

    def poll_input(self):
        self.input_handler.poll()
        self.plotView.root.after(10, self.poll_input)

    def runCommand(self, cmd: str):
        if not cmd.strip():
            return 'No command supplied'
        cmd, *args = cmd.split()
        if cmd not in self.cmds:
            m = f'Unknown command: "{cmd}"'
        else:
            m = self.cmds[cmd](*args) or ''
        return m

    def refresh(self):
        self.model.compile()
        self.plotView.draw()
        self.input_handler.compiled()

modelTime = []
plotTime = []
consoleTime = []

def timed(f):
    t = time.time()
    f()
    return time.time() - t

def mainloop() -> None:
    # parser = optparse.OptionParser()
    # parser.add_option("-h", "--help", action="help")
    # parser.add_option('-b', '--simple', action='store_const', const=InputHandler, dest='inHandler', default=InputHandler, help='Use simple IO format')
    # parser.add_option('-s', '--stream', action='store_const', const=StreamInputHandler, dest='inHandler', help='Use stream IO format')
    # parser.add_option('-l', '--lsp', action='store_const', const=LSPInputHandler, dest='inHandler', help='Use LSP IO format')
    # options, args = parser.parse_args(sys.argv)
    try:
        Controller(LSPInputHandler)
        # Controller(parser.inHandler)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    mainloop()

