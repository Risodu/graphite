from plotview import PlotView
from model import Model, Mode
from consoleview import ConsoleView, run
import time
import sys

class Controller:
    "The main control of the application"
    def __init__(self, stdscr):
        self.model = Model()
        if len(sys.argv) > 1:
            self.model.loadFile(sys.argv[1])

        self.plotView = PlotView(self.model)
        self.consoleView = ConsoleView(stdscr, self.model, self)

        self.keybinds = {Mode.NORMAL: [
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
            ('i', 'Enter insert mode', lambda: self.model.setMode(Mode.INSERT)),
            ('v', 'Enter visual mode', lambda: self.model.setMode(Mode.VISUAL)),
            (':', 'Enter command mode', lambda: self.model.setMode(Mode.COMMAND)),
            ('u', 'Undo last change', lambda: self.model.undo),
            ('r', 'Redo last change', self.model.undo),
            ('h', 'Toggle help', self.model.toggleHelp),
        ], Mode.INSERT: [
            ('Ctrl+u', 'Undo last change', self.model.undo),
            ('Ctrl+r', 'Redo last change', self.model.redo),
            ('Ctrl+v', 'Enter visual mode', lambda: self.model.setMode(Mode.VISUAL)),
            ('Ctrl+p', 'Paste text from the clipboard', self.model.paste),
            ('Ctrl+h', 'Toggle help', self.model.toggleHelp),
            ('Escape', 'Exit insert mode', lambda: self.model.setMode(Mode.NORMAL)),
            ('Right', 'Move cursor Right', lambda: self.model.movecursor(1, 0)),
            ('Left', 'Move cursor Left', lambda: self.model.movecursor(-1, 0)),
            ('Up', 'Move cursor Up', lambda: self.model.movecursor(0, -1)),
            ('Down', 'Move cursor Down', lambda: self.model.movecursor(0, 1)),
            ('Ctrl+l', 'Move cursor Right', lambda: self.model.movecursor(1, 0)),
            ('Ctrl+h', 'Move cursor Left', lambda: self.model.movecursor(-1, 0)),
            ('Ctrl+k', 'Move cursor Up', lambda: self.model.movecursor(0, -1)),
            ('Ctrl+j', 'Move cursor Down', lambda: self.model.movecursor(0, 1)),
            ('Ctrl+;', 'Comment/uncomment line', lambda: self.model.toggleCommentLine())
        ], Mode.VISUAL: [
            ('Escape', 'Exit visual mode', lambda: self.model.setMode(Mode.NORMAL)),
            ('Right', 'Move cursor Right', lambda: self.model.movecursor(1, 0)),
            ('Left', 'Move cursor Left', lambda: self.model.movecursor(-1, 0)),
            ('Up', 'Move cursor Up', lambda: self.model.movecursor(0, -1)),
            ('Down', 'Move cursor Down', lambda: self.model.movecursor(0, 1)),
            ('l', 'Move cursor Right', lambda: self.model.movecursor(1, 0)),
            ('h', 'Move cursor Left', lambda: self.model.movecursor(-1, 0)),
            ('k', 'Move cursor Up', lambda: self.model.movecursor(0, -1)),
            ('j', 'Move cursor Down', lambda: self.model.movecursor(0, 1)),
            ('y', 'Yank the selection', self.model.yank),
            ('d', 'Delete (cut) the selection', self.model.cut),
            ('h', 'Toggle help', self.model.toggleHelp),
            (';', 'Comment/uncomment selected block', lambda: self.model.toggleCommentBlock())
        ], Mode.COMMAND: [
            ('Escape', 'Exit command mode (abort)', lambda: self.model.setMode(Mode.NORMAL)),
            ('Ctrl+h', 'Toggle help', self.model.toggleHelp),
            ('Return', 'Execute the command', lambda: self.runCommand(self.model.cmdIO)),
        ]}

        self.commands = [
            (':q', 'Quit the application', lambda: self.plotView.root.quit()),
            (':w', 'Write the code to the file', lambda name = None: self.model.saveFile(name)),
            (':wq', 'Write the code to the file and quit the application', lambda name = None: (self.model.saveFile(name), self.plotView.root.quit())),
            (':e', 'Export the plot', lambda name = None: self.plotView.export(name))
        ]

        self.keymaps = {}
        for mode, defs in self.keybinds.items():
            d = {}
            for key, desc, act in defs:
                d[key] = act
            self.keymaps[mode] = d

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

        if self.model.mode != Mode.COMMAND:
            self.model.cmdIO = ''

        self.action = self.keymaps[self.model.mode].get(keysym, None)

        if self.action is None:
            self.action = self.keymaps[self.model.mode].get(keychar, None)

        if self.action is not None:
            self.action()

        if self.action is None and keychar:
            if self.model.mode == Mode.INSERT:
                self.model.write(keychar)

            if self.model.mode == Mode.COMMAND:
                self.model.cmdwrite(keychar)

        self.refresh()

    def runCommand(self, cmd: str):
        cmd, *args = cmd.split()
        if cmd not in self.cmds:
            m = f'Unknown command: "{cmd}"'
        else:
            m = self.cmds[cmd](*args) or ''
        self.model.cmdIO = m
        self.model.setMode(Mode.NORMAL)

    def refresh(self):
        modelTime.append(timed(self.model.compile))
        plotTime.append(timed(self.plotView.draw))
        consoleTime.append(timed(self.consoleView.draw))

modelTime = []
plotTime = []
consoleTime = []

def timed(f):
    t = time.time()
    f()
    return time.time() - t

def mainloop(stdscr) -> None:
    try:
        Controller(stdscr)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    run(mainloop)
    # l = len(modelTime)
    # print(l)
    # print(sum(modelTime) / l)
    # print(sum(plotTime) / l)
    # print(sum(consoleTime) / l)
