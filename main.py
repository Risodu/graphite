from plotview import PlotView
from model import Model, Mode
from consoleview import ConsoleView, run
import time

class Controller:
    "The main control of the application"
    def __init__(self, stdscr):
        self.model = Model()
        self.plotView = PlotView(self.model)
        self.consoleView = ConsoleView(stdscr, self.model, self)

        self.keybinds = {Mode.NORMAL: [
            ('+', 'Zoom plot in', lambda: self.model.zoom(0.8)),
            ('-', 'Zoom plot out', lambda: self.model.zoom(1.25)),
            ('Right', 'Shift plot Right', lambda: self.model.xrange.relshift(0.2)),
            ('Left', 'Shift plot Left', lambda: self.model.xrange.relshift(-0.2)),
            ('Up', 'Shift plot Up', lambda: self.model.yrange.relshift(0.2)),
            ('Down', 'Shift plot Down', lambda: self.model.yrange.relshift(-0.2)),
            ('i', 'Enter insert mode', lambda: self.model.setMode(Mode.INSERT)),
            ('v', 'Enter visual mode', lambda: self.model.setMode(Mode.VISUAL)),
            ('q', 'Quit the application', lambda: self.plotView.root.quit()),
            ('u', 'Undo last change', lambda: self.model.undo),
            ('r', 'Redo last change', self.model.undo),
            ('h', 'Toggle help', self.model.toggleHelp),
        ], Mode.INSERT: [
            ('Ctrl+u', 'Undo last change', self.model.undo),
            ('Ctrl+r', 'Redo last change', self.model.redo),
            ('Ctrl+v', 'Enter visual mode', lambda: self.model.setMode(Mode.VISUAL)),
            ('Ctrl+p', 'Paste text from the clipboard', self.model.paste),
            ('Ctrl+h', 'Toggle help', self.model.toggleHelp),
            ('BackSpace', 'Delete character before cursor', self.model.backspace),
            ('Delete', 'Delete character at cursor', self.model.delete),
            ('Escape', 'Exit insert mode', lambda: self.model.setMode(Mode.NORMAL)),
            ('Right', 'Move cursor Right', lambda: self.model.movecursor(1, 0)),
            ('Left', 'Move cursor Left', lambda: self.model.movecursor(-1, 0)),
            ('Up', 'Move cursor Up', lambda: self.model.movecursor(0, -1)),
            ('Down', 'Move cursor Down', lambda: self.model.movecursor(0, 1)),
        ], Mode.VISUAL: [
            ('Escape', 'Exit visual mode', lambda: self.model.setMode(Mode.NORMAL)),
            ('Right', 'Move cursor Right', lambda: self.model.movecursor(1, 0)),
            ('Left', 'Move cursor Left', lambda: self.model.movecursor(-1, 0)),
            ('Up', 'Move cursor Up', lambda: self.model.movecursor(0, -1)),
            ('Down', 'Move cursor Down', lambda: self.model.movecursor(0, 1)),
            ('y', 'Yank the selection', self.model.yank),
            ('d', 'Delete (cut) the selection', self.model.cut),
            ('h', 'Toggle help', self.model.toggleHelp),
        ]}

        self.keymaps = {}
        for mode, defs in self.keybinds.items():
            d = {}
            for key, desc, act in defs:
                d[key] = act
            self.keymaps[mode] = d

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

        # self.model.code = [f'{k}: {v}' for k, v in event.__dict__.items()]

        self.action = self.keymaps[self.model.mode].get(keysym, None)

        if self.action is None:
            self.action = self.keymaps[self.model.mode].get(keychar, None)

        if self.action is not None:
            self.action()

        if self.model.mode == Mode.INSERT and self.action is None and keychar:
            self.model.write(keychar)

        self.refresh()

    def refresh(self):
        modelTime.append(timed(self.model.compile))
        plotTime.append(timed(self.plotView.draw))
        consoleTime.append(timed(self.consoleView.draw))

from time import time

modelTime = []
plotTime = []
consoleTime = []

def timed(f):
    t = time()
    f()
    return time() - t

def mainloop(stdscr) -> None:
    try:
        Controller(stdscr)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    run(mainloop)
    l = len(modelTime)
    print(l)
    print(sum(modelTime) / l)
    print(sum(plotTime) / l)
    print(sum(consoleTime) / l)
