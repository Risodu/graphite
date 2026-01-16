import numpy as np
import typing

from graphite.eqparser import compileLine, FatalSyntaxError
from graphite.xmath import Context, Scalar, Vector, Sequence, SimpleFunction, IntegerFunction, CompiledLine, EmptyLine, DiffFunctional, SumFunctional

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

simpleFuns = [
    'abs', 'sign', 'copysign',
    'add', 'subtract', 'multiply', 'divide', 'floor_divide', 'floor', 'ceil', 'trunc', 'round',
    'mod', 'fmod', 'remainder', 'divmod', 'power', 'reciprocal', 'negative', 'positive',
    'multiply', 'divide', 'subtract', 'add', 'mod', 'fmod', 'remainder',
    'sin', 'cos', 'tan', 'arcsin', 'arccos', 'arctan', 'hypot', 'arctan2', 'degrees', 'radians', 'deg2rad', 'rad2deg',
    'sinh', 'cosh', 'tanh', 'arcsinh', 'arccosh', 'arctanh',
    'exp', 'expm1', 'exp2', 'log', 'log10', 'log2', 'log1p', 'logaddexp', 'logaddexp2',
    'sinc',
    'sqrt', 'cbrt',
    'list'
    # 'sum', 'prod', 'ediff1d', 'gradient', 'cross', 'trapz',
    # 'real_if_close', 'interp',
]

intFuns = ['gcd', 'lcm']

keywords = simpleFuns + intFuns + ['pi', 'e', 'pow', 'diff', 'sum']

constatns = {
    'pi': Scalar(np.pi), # type: ignore
    'e': Scalar(np.e)
}

functions = {i: SimpleFunction(i) for i in simpleFuns} | \
            {i: IntegerFunction(i) for i in intFuns} | \
            {
        '+': SimpleFunction('add'),
        '-': SimpleFunction('sub'),
        '--': SimpleFunction('neg'),
        '*': SimpleFunction('mul'),
        '/': SimpleFunction('div'),
        '**': SimpleFunction('pow'),
        '^': SimpleFunction('pow'),
        'pow': SimpleFunction('pow'),
        'diff': DiffFunctional(),
        'sum': SumFunctional()
}

builtins = Context(constatns, functions) # type: ignore
"The set of builtin functions availible for graphing"

# builtins = Context({}, {})

class Model:
    "Container for all the state of application"
    def __init__(self) -> None:
        self.xrange = Interval()
        self.yrange = Interval()
        self.compiled: list[tuple[CompiledLine, list[str]]] = []
        self.errors: list[str | None] = []
        self.directResults: list[str | None] = []
        self.code = ['']
        self.compile()

    def compile(self):
        "Compile the code, updating attributes `compiled` and `errors`"
        self.lines = len(self.code)
        self.compiled = [(EmptyLine(), [])] * self.lines
        self.errors = [None] * self.lines
        self.directResults = [None] * self.lines

        for i, line in enumerate(self.code):
            if not line.strip(): continue
            try:
                self.compiled[i] = compileLine(line)

            except (NameError, SyntaxError) as err:
                self.errors[i] = str(err)

    def execute(self, xspace: np.ndarray) -> list[tuple[np.ndarray, list[str]]]:
        "Execute the compiled code and return list of results"
        context = builtins.copy()
        context.variables['x'] = Vector(xspace)
        results = []

        for i, line in enumerate(self.compiled):
            try:
                line, kws = line

                res = line.evaluate(context)
                x = y = ans = None
                if len(res) == 2:
                    x, y = res
                if len(res) == 3:
                    x, y, ans = res

                if isinstance(x, Vector) and isinstance(y, Vector):
                    results.append(((x.data, y.data), kws))

                if isinstance(ans, Scalar) or isinstance(ans, Sequence):
                    self.directResults[i] = str(ans)
            except (TypeError, NameError, ValueError) as err:
                self.errors[i] = str(err)

        return results

    def zoom(self, scale: float, x = True, y = True) -> None:
        """Zoom the plot

        Arguments:
            scale (float): The scale factor
            x (bool): Whether apply to x axis
            y (bool): Whether apply to y axis
        """
        if x: self.xrange.zoom(scale)
        if y: self.yrange.zoom(scale)

if __name__ == '__main__':
    pass
    # df = compileLine('diff(x,diff(x,diff(x,sin(x))))')[0][0]
    # df = parseFundef('diff(x,sin(x))')[0][0]
    # print(df)
    # df = diffRewrite(df) # type: ignore
    # print(df)
    # for k, v in builtins.functions.items():
    #     print('\n' * 50)
    #     print(k, v.getDescription())
    #     input()
