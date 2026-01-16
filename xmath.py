import typing
import numpy as np
import math
import dataclasses

class Value:
    "Base class for any data values"
    def asInteger(self) -> typing.Any:
        return NotImplemented

    def applyFunction(self, name: str, others: list["Value"]) -> "Value":
        return NotImplemented

    def __add__(self, other: "Value") -> "Value": return self.applyFunction("add", [other])
    def __sub__(self, other: "Value") -> "Value": return self.applyFunction("sub", [other])
    def __mul__(self, other: "Value") -> "Value": return self.applyFunction("mul", [other])
    def __truediv__(self, other: "Value") -> "Value": return self.applyFunction("div", [other])
    def __pow__(self, other: "Value") -> "Value": return self.applyFunction("pow", [other])
    def __neg__(self) -> "Value": return self.applyFunction("neg", [])
    def __pos__(self) -> "Value": return self
    def __abs__(self) -> "Value": return self.applyFunction("abs", [])

@dataclasses.dataclass
class Scalar(Value):
    value: float

    functions = [{
        'neg': float.__neg__,
        'abs': abs,

        # --- trigonometric ---
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'asin': math.asin,
        'acos': math.acos,
        'atan': math.atan,
        'atan2': math.atan2,

        # --- hyperbolic ---
        'sinh': math.sinh,
        'cosh': math.cosh,
        'tanh': math.tanh,
        'asinh': math.asinh,
        'acosh': math.acosh,
        'atanh': math.atanh,

        # --- exponential & logarithmic ---
        'exp': math.exp,
        'expm1': math.expm1,
        'log': math.log,        # natural log
        'log10': math.log10,
        'log2': math.log2,
        'log1p': math.log1p,

        # --- roots & powers ---
        'sqrt': math.sqrt,
        'cbrt': lambda x: x ** (1.0 / 3.0),

        # --- rounding ---
        'floor': math.floor,
        'ceil': math.ceil,
        'trunc': math.trunc,
        'round': round,

        # --- misc ---
        'sign': lambda x: -1.0 if x < 0 else (1.0 if x > 0 else 0.0),
        'deg': math.degrees,
        'rad': math.radians,
    },
    {
        'add': float.__add__,
        'sub': float.__sub__,
        'mul': float.__mul__,
        'div': float.__truediv__,
        'pow': math.pow,
    }]

    def __str__(self) -> str:
        return str(self.value)

    def asInteger(self):
        return round(self.value)

    def applyFunction(self, name: str, others: list["Value"]) -> "Value":
        argTypes = ', '.join(i.__class__.__name__ for i in [self, *others])
        noFunErr = TypeError(f'No overload of {name} takes arguments {argTypes}')

        if name == 'list':
            return Sequence([self, *others])

        if len(others) == 0:
            fn = Scalar.functions[0].get(name, None)
            if fn is None:
                raise noFunErr
            return Scalar(fn(self.value))

        if len(others) == 1:
            o = others[0]

            if isinstance(o, Scalar):
                fn = Scalar.functions[1].get(name, None)
                if fn is None: raise noFunErr
                return Scalar(fn(self.value, o.value))
            elif isinstance(o, Vector):
                fn = Vector.functions[1].get(name, None)
                if fn is None: raise noFunErr
                return Vector(fn(self.value, o.data))
            elif isinstance(o, Sequence):
                return Sequence([self.applyFunction(name, [i]) for i in o.items])
            else:
                raise noFunErr

        raise noFunErr

@dataclasses.dataclass
class Vector(Value):
    data: np.ndarray

    functions = [{
        # --- unary arithmetic ---
        'neg': np.negative,
        'abs': np.abs,

        # --- trigonometric ---
        'sin': np.sin,
        'cos': np.cos,
        'tan': np.tan,
        'asin': np.arcsin,
        'acos': np.arccos,
        'atan': np.arctan,
        'atan2': np.arctan2,

        # --- hyperbolic ---
        'sinh': np.sinh,
        'cosh': np.cosh,
        'tanh': np.tanh,
        'asinh': np.arcsinh,
        'acosh': np.arccosh,
        'atanh': np.arctanh,

        # --- exponential & logarithmic ---
        'exp': np.exp,
        'expm1': np.expm1,
        'log': np.log,
        'log10': np.log10,
        'log2': np.log2,
        'log1p': np.log1p,

        # --- roots & powers ---
        'sqrt': np.sqrt,
        'cbrt': np.cbrt,

        # --- rounding ---
        'floor': np.floor,
        'ceil': np.ceil,
        'trunc': np.trunc,
        'round': np.round,

        # --- misc ---
        'sign': np.sign,
        'deg': np.degrees,
        'rad': np.radians,
    },
    {
        # --- binary arithmetic ---
        'add': np.add,
        'sub': np.subtract,
        'mul': np.multiply,
        'div': np.true_divide,
        'pow': np.power,
    }]

    def asInteger(self):
        return self.data.astype(np.int64)

    def applyFunction(self, name: str, others: list["Value"]) -> "Value":
        argTypes = ', '.join(i.__class__.__name__ for i in [self, *others])
        noFunErr = TypeError(f'No overload of {name} takes arguments {argTypes}')

        if name == 'list':
            return Sequence([self, *others])

        if len(others) == 0:
            fn = Vector.functions[0].get(name, None)
            if fn is None:
                raise noFunErr
            return Vector(fn(self.data))

        if len(others) == 1:
            o = others[0]
            if isinstance(o, Scalar) or isinstance(o, Vector):
                fn = Vector.functions[1].get(name, None)
                if fn is None: raise noFunErr
                return Vector(fn(self.data, o.value if isinstance(o, Scalar) else o.data))
            elif isinstance(o, Sequence):
                return Sequence([self.applyFunction(name, [i]) for i in o.items])
            else:
                raise noFunErr

        raise noFunErr

@dataclasses.dataclass
class Sequence(Value):
    items: list[Value]   # for jagged / per-element results

    def __init__(self, args: list[Value]):
        self.items = args

    def asInteger(self):
        return [i.asInteger() for i in self.items]

    def applyFunction(self, name: str, others: list["Value"]) -> "Value":
        argTypes = ', '.join(i.__class__.__name__ for i in [self, *others])
        noFunErr = TypeError(f'No overload of {name} takes arguments {argTypes}')

        if name == 'get':
            if not len(others) == 1 or not isinstance(others[0], Scalar):
                raise noFunErr
            return self.items[int(others[0].value)]

        if len(others) == 0:
            return Sequence([i.applyFunction(name, []) for i in self.items])

        if len(others) == 1:
            o = others[0]
            if isinstance(o, Sequence):
                return Sequence([a.applyFunction(name, [b]) for a, b in zip(self.items, o.items)])
            if isinstance(o, Scalar) or isinstance(o, Vector):
                return Sequence([i.applyFunction(name, [o]) for i in self.items])

        raise noFunErr

    def __str__(self) -> str:
        return '[' + ', '.join(map(str, self.items)) + ']'

class Context:
    "Context of defined variables and functions that can be used during expreesion evaluation"
    def __init__(self, variables: dict[str, Value], functions: dict[str, "Function"]) -> None:
        self.variables = variables
        self.functions = functions

    def copy(self):
        "Creates an independent copy of the context"
        return Context(self.variables.copy(), self.functions.copy())

class Expression:
    "Base class for expressions"
    def evaluate(self, context: Context) -> Value:
        "Evaluates this expression in the given context"
        return NotImplemented

    def getRequirements(self) -> list[str]:
        "Returns list of variables and functions that has to be in the context for the proper evaluation"
        return NotImplemented

    def __add__(self, other: "Expression") -> "Expression":
        return FunCall('+', [self, other])

    def __sub__(self, other: "Expression") -> "Expression":
        return FunCall('-', [self, other])

    def __neg__(self) -> "Expression":
        return FunCall('--', [self])

    def __mul__(self, other: "Expression") -> "Expression":
        return FunCall('*', [self, other])

    def __truediv__(self, other: "Expression") -> "Expression":
        return FunCall('/', [self, other])

    def __pow__(self, other: "Expression") -> "Expression":
        return FunCall('**', [self, other])

    def diff(self, param: "Variable") -> "Expression":
        return FunCall('diff', [param, self])

class Constant(Expression):
    "A constant numeric value"
    def __init__(self, value: Value) -> None:
        self.value = value

    def evaluate(self, context: Context) -> Value:
        return self.value
 
    def getRequirements(self) -> list[str]:
        return []

    def __repr__(self) -> str:
        return f'Constant({self.value})'

    def __str__(self) -> str:
        return str(self.value)

class Variable(Expression):
    "Single variable which value is provided by the context"
    def __init__(self, id: str) -> None:
        self.id = id

    def evaluate(self, context: Context) -> Value:
        if self.id not in context.variables:
            raise NameError(f'Variable {self.id} not defined')
        return context.variables[self.id]

    def getRequirements(self) -> list[str]:
        return [self.id]

    def __repr__(self) -> str:
        return f'Variable("{self.id}")'

    def __str__(self) -> str:
        return self.id

class FunCall(Expression):
    "A call of some function defined in the context"
    def __init__(self, fname: str, args: list[Expression]) -> None:
        self.fname = fname
        self.args = args

    def evaluate(self, context: Context) -> Value:
        if self.fname not in context.functions:
            raise NameError(f'Function {self.fname} not defined')

        return context.functions[self.fname].evaluate(context, self.args)

    def getRequirements(self) -> list[str]:
        res = [self.fname]
        for arg in self.args:
            res += arg.getRequirements()
        return res

    def __repr__(self) -> str:
        return f'FunCall("{self.fname}", {self.args})'

    def __str__(self) -> str:
        if self.fname in ('+', '-', '*', '/', '**'):
            return f'{self.args[0]} {self.fname} {self.args[1]}'
        return f'{self.fname}({", ".join(map(str, self.args))})'

class Function:
    "Base class for objects that represent function"
    def evaluate(self, context: Context, args: list[Expression]) -> Value:
        return NotImplemented

    def getDescription(self) -> str:
        return NotImplemented

class SimpleFunction(Function):
    "First-order function defined by single callable"
    def __init__(self, name: str) -> None:
        self.name = name

    def evaluate(self, context: Context, args: list[Expression]) -> Value:
        vals = [arg.evaluate(context) for arg in args]
        return vals[0].applyFunction(self.name, vals[1:])

    def getDescription(self) -> str:
        return self.name.__doc__ or ''

class IntegerFunction(SimpleFunction):
    "`SimpleFunction` that converts data into integer type before passing it to the callable"
    def evaluate(self, context: Context, args: list[Expression]) -> Value:
        vals = [arg.evaluate(context).asInteger() for arg in args]
        return vals[0].applyFunction(self.name, vals[1:])

class UserFunction(Function):
    """The compiled definition of function

    Attributes:
        args (list[str]): List of argument names
        expr (Expression): The expression that contains the function definition
    """
    def __init__(self, args: list[str], expr: Expression) -> None:
        self.args = args
        self.expr = expr

    def evaluate(self, context: Context, args: list[Expression]) -> Value:
        "Call the function in the given context on the given arguments"
        if len(args) != len(self.args):
            raise TypeError(f'expected {len(self.args)} paramenters, got {len(args)}')

        context = context.copy()
        for k, v in zip(self.args, args):
            context.variables[k] = v.evaluate(context)

        return self.expr.evaluate(context)

    def getDescription(self) -> str:
        return 'User defined'

class DiffFunctional(Function):
    "Functional that computes derivative of function"

    EPS = Scalar(0.0000001)
    def __init__(self) -> None:
        pass

    def evaluate(self, context: Context, args: list[Expression]) -> Value:
        if len(args) != 2:
            raise TypeError(f'diff expected 2 paramenters, got {len(args)}')

        param, expr = args
        if not isinstance(param, Variable):
            raise TypeError(f'differentiated variable must be variable')

        c1 = context.copy()
        c2 = context.copy()
        c2.variables[param.id] = param.evaluate(context) + DiffFunctional.EPS

        return (expr.evaluate(c2) - expr.evaluate(c1)) / DiffFunctional.EPS

    def getDescription(self) -> str:
        return 'Computes derivative of given function against given variable. Example: diff(sin(t),t) = cos(t)'

class SumFunctional(Function):
    "Functional that computes sum of expression in given list of numbers"

    def __init__(self) -> None:
        pass

    def evaluate(self, context: Context, args: list[Expression]) -> Value:
        raise TypeError(f'sum is currently work in progress')
        if len(args) != 4:
            raise TypeError(f'sum expected 4 paramenters, got {len(args)}')

        param, start, stop, expr = args
        if not isinstance(param, Variable):
            raise TypeError(f'summation variable must be variable')

        start = start.evaluate(context).asInteger()
        stop = stop.evaluate(context).asInteger() + 1
        steps = stop - start

        if steps.shape == ():
            c = context.copy()
            c.variables[param.id] = start
            res = expr.evaluate(c)
            for i in range(start + 1, stop):
                c.variables[param.id] = np.array(i)
                res += expr.evaluate(c)
            return res

        if start.shape == (): start = np.array([start])
        if stop.shape == (): stop = np.array([stop])

        c = context.copy()

        res = np.empty_like(steps, dtype=float)
        for i in range(steps.shape[0]):

            for k, v in context.variables.items():
                if isinstance(v, np.ndarray) and v.shape == steps.shape:
                    c.variables[k] = v[i]
                else:
                    c.variables[k] = v

            c.variables[param.id] = np.arange(start[min(i, start.shape[0] - 1)], stop[min(i, stop.shape[0] - 1)])

            r = expr.evaluate(c)
            res[i] = np.sum(r, 0) if sum(r.shape) else 0

        return res

    def getDescription(self) -> str:
        return 'Computes derivative of given function against given variable. Example: diff(sin(t),t) = cos(t)'

# import inspect
# import sys
# sys.setrecursionlimit(250)
def diffRewrite(expr: Expression) -> Expression:
    "Rewrite expression such that the number of DiffFunctional instances is minimized"
    if not isinstance(expr, FunCall): return expr
    if expr.fname != 'diff':
        return FunCall(expr.fname, [diffRewrite(a) for a in expr.args])

    if len(expr.args) != 2:
        raise TypeError(f'diff expected 2 paramenters, got {len(expr.args)}')

    param, subexpr = expr.args
    if not isinstance(param, Variable):
        raise TypeError(f'differentiated variable must be variable')

    subexpr = diffRewrite(subexpr)

    if isinstance(subexpr, Constant):
        return Constant(Scalar(0))

    if isinstance(subexpr, Variable):
        return Constant(Scalar(1 if subexpr.id == param.id else 0))

    if isinstance(subexpr, FunCall):
        fn = subexpr.fname

        inners = [diffRewrite(a.diff(param)) for a in subexpr.args]
        if fn == '+':
            return inners[0] + inners[1]

        if fn == '-':
            return inners[0] - inners[1]

        if fn == '--':
            return -inners[0]

        if fn == '*':
            return subexpr.args[1] * inners[0] + subexpr.args[0] * inners[1]

        if fn == '/':
            return (subexpr.args[1] * inners[0] - subexpr.args[0] * inners[1]) / (subexpr.args[1] ** Constant(Scalar(2)))

        if fn == 'sin':
            return FunCall('cos', subexpr.args) * inners[0]

        if fn == 'cos':
            return -FunCall('sin', subexpr.args) * inners[0]

        if fn == 'exp':
            return subexpr * inners[0]

        if fn == 'log':
            return inners[0] / subexpr.args[0]

    return expr

class CompiledLine:
    def evaluate(self, context) -> list[Value]:
        """Evaluate the compiled line in given context.

        Returns:
            list[Value]: Pair of two Values, representing datapoints to plot. May include third value: the result of function call, to be displayed to the user.
        """
        return [Vector(np.empty((0,))), Vector(np.empty((0,)))]

class EmptyLine(CompiledLine):
    pass

class FunctionDefinition(CompiledLine):
    def __init__(self, name: str, definition: UserFunction) -> None:
        self.name = name
        self.definition = definition

    def evaluate(self, context) -> list[Value]:
        self.definition.expr = diffRewrite(self.definition.expr)

        context.functions[self.name] = self.definition
        if len(self.definition.args) != 1:
            return super().evaluate(context)

        c = context.copy()
        param = self.definition.args[0]

        if self.name == 'r': # polar plots
            size = len(c.variables['x'].data) if isinstance(c.variables['x'], Vector) else 1000
            theta = np.linspace(0, 2 * np.pi, size)
            c.variables[param] = Vector(theta)
            radius = self.definition.evaluate(c, [Variable(param)])
            x = radius * Vector(np.cos(theta))
            y = radius * Vector(np.sin(theta))
            return [x, y, radius]
        else:
            c.variables[param] = c.variables['x']
            y = self.definition.evaluate(c, [Variable(param)])
            context.variables[self.name] = y

            res = [c.variables['x'], y, y]

        return res

class ParamPlot(CompiledLine):
    """The compiled definition of parametric plot

    Attributes:
        xexpr (list[Expression]): Expression that defines x-coordinate
        yexpr (list[Expression]): Expression that defines y-coordinate
        var (str): Name of the parameter
        start (Expression): Initial value of the parameter
        end (Expression): Final value of the parameter
    """
    def __init__(self, xexpr: Expression, yexpr: Expression, var: str, start: Expression, end: Expression) -> None:
        self.xexpr = xexpr
        self.yexpr = yexpr
        self.var = var
        self.start = start
        self.end = end

    def evaluate(self, context: Context) -> list[Value]:
        "Evaluate the parametric plot"

        context = context.copy()
        start = self.start.evaluate(context)
        end = self.end.evaluate(context)
        if not isinstance(start, Scalar): raise TypeError('Parametric plot start must be scalar!')
        if not isinstance(end, Scalar): raise TypeError('Parametric plot start must be scalar!')
        t = np.linspace(start.value, end.value, 1000)
        context.variables[self.var] = Vector(t)

        return [self.xexpr.evaluate(context), self.yexpr.evaluate(context)]
