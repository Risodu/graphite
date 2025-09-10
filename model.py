import numpy as np
import typing
import re
import enum
import pyperclip

from eqparser import parseFundef, parseParamPlot, FatalSyntaxError
from xmath import Context, Variable, Constant, SimpleFunction, IntegerFunction, UserFunction, ParamPlot, DiffFunctional, SumFunctional

class Mode(enum.Enum):
    "Current mode of the application"
    NORMAL = 'Normal'
    INSERT = 'Insert'
    VISUAL = 'Visual'

class Interval:
    "Span determined by its endpoints."
    def __init__(self, s: float = -10, e: float = 10):
        self.s: float = s
        self.e: float = e

    def len(self) -> float:
        "Return length of the interval"
        return self.e - self.s

    def mid(self) -> float:
        "Return the midpoint of the interval"
        return (self.s + self.e) * 0.5

    def zoom(self, scale: float) -> None:
        "Multiply the interval length by `scale` while maintaining its midpoint"
        delta = self.len() * 0.5 * scale
        mid = self.mid()
        self.s = mid - delta
        self.e = mid + delta
    
    def copyzoom(self, scale: float) -> "Interval":
        "Return interval with `scale` times longer and the same midpoint"
        delta = self.len() * 0.5 * scale
        mid = self.mid()
        return Interval(mid - delta, mid + delta)

    def relshift(self, step: float) -> None:
        "Shift the interval by `step * its length`"
        delta = self.len() * step
        self.s += delta
        self.e += delta

    def absshift(self, step: float) -> None:
        "Shift the interval by `step`"
        self.s += step
        self.e += step

    def __iter__(self) -> typing.Iterator[float]:
        yield self.s
        yield self.e

def compileFunction(line: str):
    toks = parseFundef(line)
    definition = toks[-1]
    name = '' if len(toks) == 1 else toks[0]
    
    if len(toks) <= 2:
        params = ['x']

    else:
        if any(not isinstance(v, Variable) for v in toks[1]):
            raise SyntaxError('Function definition parameters must be variable names')
        params = [v.id for v in toks[1]] # type: ignore

    return name, UserFunction(params, definition)

def compileParamPlot(line: str):
    toks = parseParamPlot(line)
    if len(toks) != 2:
        raise SyntaxError('Parametric plot require parameter definition (such as "(cos(t),sin(t))[t,0,1]")')
    exprs, params = toks
    if len(exprs) != 2:
        raise SyntaxError(f'Parametric plot expected 2 expressions, got {len(exprs)}')
    if len(params) != 3:
        raise SyntaxError(f'Parametric plot expected 3 parameters, got {len(params)}')

    if not isinstance(params[0], Variable):
        raise SyntaxError(f'First parameter of parametric plot must be variable name')
    if not isinstance(params[1], Constant):
        raise SyntaxError(f'Second parameter of parametric plot must be constant name')
    if not isinstance(params[2], Constant):
        raise SyntaxError(f'Third parameter of parametric plot must be constant name')

    return ParamPlot(exprs[0], exprs[1], params[0].id, params[1].value, params[2].value)

def compileLine(line: str):
    try:
        return compileFunction(line)
    except FatalSyntaxError as err:
        pass

    try:
        return compileParamPlot(line)
    except FatalSyntaxError as err:
        raise err

simpleFuns = [
    'abs', 'sign', 'copysign',
    'add', 'subtract', 'multiply', 'divide', 'floor_divide', 'floor', 'ceil', 'trunc', 'round',
    'mod', 'fmod', 'remainder', 'divmod', 'power', 'reciprocal', 'negative', 'positive',
    'multiply', 'divide', 'subtract', 'add', 'mod', 'fmod', 'remainder',
    'sin', 'cos', 'tan', 'arcsin', 'arccos', 'arctan', 'hypot', 'arctan2', 'degrees', 'radians', 'deg2rad', 'rad2deg',
    'sinh', 'cosh', 'tanh', 'arcsinh', 'arccosh', 'arctanh',
    'exp', 'expm1', 'exp2', 'log', 'log10', 'log2', 'log1p', 'logaddexp', 'logaddexp2',
    'sinc',
    'sqrt', 'cbrt'
    # 'sum', 'prod', 'ediff1d', 'gradient', 'cross', 'trapz',
    # 'real_if_close', 'interp',
]

intFuns = ['gcd', 'lcm']

keywords = simpleFuns + intFuns + ['pi', 'e', 'pow', 'diff', 'sum']

constatns = {
    'pi': np.pi, # type: ignore
    'e': np.e
}

functions = {i: SimpleFunction(np.__dict__[i]) for i in simpleFuns} | \
            {i: IntegerFunction(np.__dict__[i]) for i in intFuns} | \
            {
        '+': SimpleFunction(np.add),
        '-': SimpleFunction(np.subtract),
        '--': SimpleFunction(np.negative),
        '*': SimpleFunction(np.multiply),
        '/': SimpleFunction(np.true_divide),
        '**': SimpleFunction(np.power),
        '^': SimpleFunction(np.power),
        'pow': SimpleFunction(np.power),
        'diff': DiffFunctional(),
        'sum': SumFunctional()
}

builtins = Context(constatns, functions) # type: ignore
"The set of builtin functions availible for graphing"

# builtins = Context({}, {})

def undoable(f):
    def wrapper(self, *args, **kwargs):
        self.undohistory = []
        self.history.append(self.save())
        f(self, *args, **kwargs)
    return wrapper

class Model:
    "Container for all the state of application"
    def __init__(self) -> None:
        self.xrange = Interval()
        self.yrange = Interval()
        self.compiled: list[tuple[str, UserFunction] | None | ParamPlot] = []
        self.errors: list[str | None] = []
        self.code = ['sin(x)']
        self.history = []
        self.undohistory = []
        self.cursor = [0, 0]
        self.visualBegin = [0, 0]
        self.mode = Mode.NORMAL
        self.help = False
        self.compile()

    @property
    def flatCode(self) -> str:
        return '\n'.join(self.code)

    @flatCode.setter
    def flatCode(self, c: str):
        self.code = c.split('\n')

    def flatpos(self, x, y):
        c = x
        for i in range(y):
            c += len(self.code[i]) + 1
        return c

    def compile(self):
        "Compile the code, updating attributes `compiled` and `errors`"
        self.lines = len(self.code)
        self.compiled = [None] * self.lines
        self.errors = [None] * self.lines
        
        for i, line in enumerate(self.code):
            if not line.strip(): continue
            try:
                self.compiled[i] = compileLine(line)

            except (NameError, SyntaxError) as err:
                self.errors[i] = str(err)

    def execute(self, x: np.ndarray) -> list[np.ndarray]:
        "Execute the compiled code and return list of results"
        context = builtins.copy()
        results = []

        for i, line in enumerate(self.compiled):
            if line is None: continue

            if isinstance(line, ParamPlot):
                try:
                    results.append(line.evaluate(context))
                except (TypeError, NameError) as err:
                    self.errors[i] = str(err)

            else:
                name, func = line
                context.functions[name] = func
                if len(func.args) != 1:
                    continue
                
                try:
                    c = context.copy()
                    c.variables['x'] = x
                    res = func.evaluate(c, [Variable('x')])
                    context.variables[name] = res
                    results.append([x, res])
                except (TypeError, NameError) as err:
                    self.errors[i] = str(err)

        return results

    def setMode(self, m: Mode) -> None:
        "Set the `mode` to `m`"
        if m == Mode.VISUAL:
            self.visualBegin = self.cursor.copy()
        self.mode = m

    def toggleHelp(self) -> None:
        self.help = not self.help

    def zoom(self, scale: float, x = True, y = True) -> None:
        """Zoom the plot
        
        Arguments:
            scale (float): The scale factor
            x (bool): Whether apply to x axis
            y (bool): Whether apply to y axis
        """
        if x: self.xrange.zoom(scale)
        if y: self.yrange.zoom(scale)

    @undoable
    def write(self, s: str) -> None:
        "Write the string on the screen at the cursor position"
        x, y = self.cursor
        parts = (self.code[y][:x] + s.replace('\r', '\n') + self.code[y][x:]).split('\n')
        self.code[y] = parts[0]
        for p in parts[:0:-1]:
            self.code.insert(y + 1, p)
        
        self.cursor[0] += len(s)
        while self.cursor[0] > len(self.code[self.cursor[1]]):
            self.cursor[0] -= len(self.code[self.cursor[1]]) + 1
            self.cursor[1] += 1

    def movecursor(self, x: int, y: int) -> None:
        "Move the cursor"
        self.cursor[1] = min(len(self.code) - 1, max(self.cursor[1] + y, 0))
        self.cursor[0] = min(len(self.code[self.cursor[1]]), max(self.cursor[0] + x, 0))

    @undoable
    def backspace(self):
        "Delete character before the cursor"
        x, y = self.cursor
        if x == 0: return
        self.code[y] = self.code[y][:x - 1] + self.code[y][x:]
        self.cursor[0] -= 1

    @undoable
    def delete(self):
        "Delete character after the cursor"
        x, y = self.cursor
        if x == len(self.code[y]): return
        self.code[y] = self.code[y][:x] + self.code[y][x + 1:]

    def relchar(self, c):
        x = c
        y = 0
        while x > len(self.code[y]):
            x -= len(self.code[y]) + 1
            y += 1
        return [x, y]

    def save(self):
        return [self.code.copy(), self.cursor.copy()]

    def load(self, state):
        self.code = state[0].copy()
        self.cursor = state[1].copy()

    def undo(self):
        if not self.history: return
        self.undohistory.append(self.save())
        s = self.history.pop()
        self.load(s)

    def redo(self):
        if not self.undohistory: return
        self.history.append(self.save())
        s = self.undohistory.pop()
        self.load(s)

    def yank(self):
        start, end = sorted([self.flatpos(*self.visualBegin), self.flatpos(*self.cursor)])
        s = '\n'.join(self.code) + '\n'
        pyperclip.copy(s[start : end + 1])
        self.setMode(Mode.NORMAL)

    def paste(self):
        self.write(pyperclip.paste())

    def cut(self):
        start, end = sorted([self.flatpos(*self.visualBegin), self.flatpos(*self.cursor)])
        s = '\n'.join(self.code) + '\n'
        pyperclip.copy(s[start : end + 1])
        s = s[:start] + s[end + 1:]
        self.code = s.split('\n')
        self.cursor = self.relchar(start)
        self.setMode(Mode.NORMAL)

if __name__ == '__main__':
    for k, v in builtins.functions.items():
        print('\n' * 50)
        print(k, v.getDescription())
        input()
