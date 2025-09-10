import curses
import enum

from model import Model, Mode, keywords
from tokenizer import tokenize

class StyleEnum(enum.IntEnum):
    "Styles of the text"
    NORMAL = 1
    LINENO = 2
    HIGHLIGHT = 3
    ERROR = 4
    MODE = 5
    SELECT = 6
    KEYWORD = 7
    IDENTIFIER = 8
    CONSTANT = 9

class ConsoleView:
    "Class that manages the view of the console window"
    def __init__(self, scr: curses.window, model: Model, controller) -> None:
        self.scr = scr
        self.model = model
        self.controller = controller
        curses.init_pair(StyleEnum.NORMAL, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(StyleEnum.HIGHLIGHT, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.COLORS += 1
        curses.init_color(8, 500, 500, 500)
        curses.init_pair(StyleEnum.LINENO, 8, curses.COLOR_BLACK)
        curses.init_pair(StyleEnum.ERROR, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(StyleEnum.MODE, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(StyleEnum.SELECT, curses.COLOR_WHITE, curses.COLOR_CYAN)
        curses.init_pair(StyleEnum.KEYWORD, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(StyleEnum.IDENTIFIER, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(StyleEnum.CONSTANT, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.curs_set(0)
        self.draw()

    def draw(self) -> None:
        "Refresh the screen"
        self.scr.clear()

        self.maxy, self.maxx = self.scr.getmaxyx()

        if self.model.help:
            self.drawHelp()
        else:
            self.drawCode()

        self.scr.addstr(self.maxy - 1, 0, str(self.model.mode), curses.color_pair(StyleEnum.MODE))
        self.scr.refresh()

    def drawCode(self):
        lineno = 0
        codeStart = 6
        for i, line in enumerate(self.model.code):
            line += ' '
            self.scr.addstr(lineno, 4 - len(str(i + 1)), str(i + 1), curses.color_pair(StyleEnum.LINENO))

            try:
                tokens = tokenize(line)
            except Exception as err:
                tokens = [('other', str(line), 0)]

            for kind, text, start in tokens:
                if kind == 'constant':
                    color = StyleEnum.CONSTANT
                elif kind == 'identifier':
                    color = StyleEnum.KEYWORD if text in keywords else StyleEnum.IDENTIFIER
                else:
                    color = StyleEnum.NORMAL
                self.scr.addstr(lineno, codeStart + start, text, curses.color_pair(color))

            if i == self.model.cursor[1] and self.model.mode == Mode.INSERT:
                x, y = self.model.cursor
                c = line[x] # if x < len(self.model.code[y]) else ' '
                self.scr.addch(lineno, x + codeStart, c, curses.color_pair(StyleEnum.HIGHLIGHT))
            
            if self.model.mode == Mode.VISUAL:
                visstart, visend = sorted([self.model.cursor, self.model.visualBegin], key=lambda x: x[::-1])
                sx, sy = visstart
                ex, ey = visend
                if sy < i < ey:
                    self.scr.addstr(lineno, codeStart, line, curses.color_pair(StyleEnum.SELECT))

                if sy == i < ey:
                    self.scr.addstr(lineno, codeStart + sx, line[sx:], curses.color_pair(StyleEnum.SELECT))

                if sy < i == ey:
                    self.scr.addstr(lineno, codeStart, line[:ex + 1], curses.color_pair(StyleEnum.SELECT))

                if sy == i == ey:
                    self.scr.addstr(lineno, codeStart + sx, line[sx:ex + 1], curses.color_pair(StyleEnum.SELECT))

            lineno += 1
            err = self.model.errors[i]
            if err:
                self.scr.addstr(lineno, 3, err, curses.color_pair(StyleEnum.ERROR))
                lineno += 1

    def drawHelp(self):
        for i, keybind in enumerate(self.controller.keybinds[self.model.mode]):
            bind, desc, _ = keybind
            self.scr.addstr(i, 2, bind)
            self.scr.addstr(i, 12, desc)

run = curses.wrapper
