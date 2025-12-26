import numpy as np
import typing

from graphite.eqparser import parseFundef, parseParamPlot, parseNull, FatalSyntaxError
from graphite.xmath import Context, Variable, Constant, SimpleFunction, IntegerFunction, UserFunction, ParamPlot, DiffFunctional, SumFunctional, diffRewrite

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
    toks, kws = parseFundef(line)
    definition = toks[-1]
    name = '' if len(toks) == 1 else toks[0]

    if len(toks) <= 2:
        params = ['x']

    else:
        if any(not isinstance(v, Variable) for v in toks[1]):
            raise SyntaxError('Function definition parameters must be variable names')
        params = [v.id for v in toks[1]] # type: ignore

    return (name, UserFunction(params, definition)), kws

def compileParamPlot(line: str):
    toks, kws = parseParamPlot(line)
    if len(toks) != 2:
        raise SyntaxError('Parametric plot require parameter definition (such as "(cos(t),sin(t))[t,0,1]")')
    exprs, params = toks
    if len(exprs) != 2:
        raise SyntaxError(f'Parametric plot expected 2 expressions, got {len(exprs)}')
    if len(params) != 3:
        raise SyntaxError(f'Parametric plot expected 3 parameters, got {len(params)}')

    if not isinstance(params[0], Variable):
        raise SyntaxError(f'First parameter of parametric plot must be variable name')

    return ParamPlot(exprs[0], exprs[1], params[0].id, params[1], params[2]), kws

def compileNull(line: str):
    parseNull(line)

def compileLine(line: str):
    err = None
    for f in [compileFunction, compileParamPlot, compileNull]:
        try:
            return f(line)
        except FatalSyntaxError as e:
            err = e

    raise err # type: ignore

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

class Model:
    "Container for all the state of application"
    def __init__(self) -> None:
        self.xrange = Interval()
        self.yrange = Interval()
        self.compiled: list[tuple[tuple[str, UserFunction] | ParamPlot, list[str]] | None] = []
        self.errors: list[str | None] = []
        self.code = ['']
        self.compile()

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

    def execute(self, x: np.ndarray) -> list[tuple[np.ndarray, list[str]]]:
        "Execute the compiled code and return list of results"
        context = builtins.copy()
        results = []

        for i, line in enumerate(self.compiled):
            if line is None: continue
            line, kws = line

            if isinstance(line, ParamPlot):
                try:
                    results.append((line.evaluate(context), kws))
                except (TypeError, NameError) as err:
                    self.errors[i] = str(err)

            else:
                name, func = line
                try:
                    func.expr = diffRewrite(func.expr)
                except TypeError as err:
                    self.errors[i] = str(i)
                    continue

                context.functions[name] = func
                if len(func.args) != 1:
                    continue

                try:
                    c = context.copy()
                    c.variables['x'] = x
                    res = func.evaluate(c, [Variable('x')])
                    context.variables[name] = res
                    if 'hide' not in kws:
                        results.append(([x, res], kws))
                except (TypeError, NameError) as err:
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
    df = parseFundef('diff(x,diff(x,diff(x,sin(x))))')[0][0]
    # df = parseFundef('diff(x,sin(x))')[0][0]
    print(df)
    df = diffRewrite(df) # type: ignore
    print(df)
    # for k, v in builtins.functions.items():
    #     print('\n' * 50)
    #     print(k, v.getDescription())
    #     input()
