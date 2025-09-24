import typing
import numpy as np

class Context:
    "Context of defined variables and functions that can be used during expreesion evaluation"
    def __init__(self, variables: dict[str, np.ndarray], functions: dict[str, "Function"]) -> None:
        self.variables = variables
        self.functions = functions

    def copy(self):
        "Creates an independent copy of the context"
        return Context(self.variables.copy(), self.functions.copy())

class Expression:
    "Base class for expressions"
    def evaluate(self, context: Context) -> np.ndarray:
        "Evaluates this expression in the given context"
        return NotImplemented

    def getRequirements(self) -> list[str]:
        "Returns list of variables and functions that has to be in the context for the proper evaluation"
        return NotImplemented

class Constant(Expression):
    "A constant numeric value"
    def __init__(self, value: float) -> None:
        self.value = value

    def evaluate(self, context: Context) -> np.ndarray:
        return np.array(self.value)
 
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

    def evaluate(self, context: Context) -> np.ndarray:
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

    def evaluate(self, context: Context) -> np.ndarray:
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
        return f'{self.fname}({", ".join(map(str, self.args))})'

class Function:
    "Base class for objects that represent function"
    def evaluate(self, context: Context, args: list[Expression]) -> np.ndarray:
        return NotImplemented

    def getDescription(self) -> str:
        return NotImplemented

class SimpleFunction(Function):
    "First-order function defined by single callable"
    def __init__(self, callable: typing.Callable) -> None:
        self.callable = callable

    def evaluate(self, context: Context, args: list[Expression]) -> np.ndarray:
        return self.callable(*(arg.evaluate(context) for arg in args))

    def getDescription(self) -> str:
        return self.callable.__doc__ or ''

class IntegerFunction(SimpleFunction):
    "`SimpleFunction` that converts data into integer type before passing it to the callable"
    def evaluate(self, context: Context, args: list[Expression]) -> np.ndarray:
        return self.callable(*(arg.evaluate(context).astype(np.int64) for arg in args))

class UserFunction(Function):
    """The compiled definition of function
    
    Attributes:
        args (list[str]): List of argument names
        expr (Expression): The expression that contains the function definition
    """
    def __init__(self, args: list[str], expr: Expression) -> None:
        self.args = args
        self.expr = expr

    def evaluate(self, context: Context, args: list[Expression]) -> np.ndarray:
        "Call the function in the given context on the given arguments"
        if len(args) != len(self.args):
            raise TypeError(f'expected {len(self.args)} paramenters, got {len(args)}')
        
        context = context.copy()
        for k, v in zip(self.args, args):
            context.variables[k] = v.evaluate(context)

        return self.expr.evaluate(context) + np.zeros_like(args[0].evaluate(context))

    def getDescription(self) -> str:
        return 'User defined'

class DiffFunctional(Function):
    "Functional that computes derivative of function"
    
    EPS = 0.0000001
    def __init__(self) -> None:
        pass

    def evaluate(self, context: Context, args: list[Expression]) -> np.ndarray:
        if len(args) != 2:
            raise TypeError(f'diff expected 2 paramenters, got {len(args)}')

        param, expr = args
        if not isinstance(param, Variable):
            raise TypeError(f'differentiated variable must be variable')

        c1 = context.copy()
        c2 = context.copy()
        c2.variables[param.id] = param.evaluate(context) + DiffFunctional.EPS

        return (expr.evaluate(c2) - expr.evaluate(c1)) / DiffFunctional.EPS + np.zeros_like(context.variables[param.id])

    def getDescription(self) -> str:
        return 'Computes derivative of given function against given variable. Example: diff(sin(t),t) = cos(t)'

class SumFunctional(Function):
    "Functional that computes sum of expression in given list of numbers"
    
    def __init__(self) -> None:
        pass

    def evaluate(self, context: Context, args: list[Expression]) -> np.ndarray:
        if len(args) != 4:
            raise TypeError(f'sum expected 4 paramenters, got {len(args)}')

        param, start, stop, expr = args
        if not isinstance(param, Variable):
            raise TypeError(f'summation variable must be variable')

        start = start.evaluate(context).astype(np.int64)
        stop = stop.evaluate(context).astype(np.int64) + 1
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

def extract(arr: np.ndarray):
    while arr.shape: arr = arr[0]
    return arr

class ParamPlot:
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

    def evaluate(self, context: Context) -> list[np.ndarray]:
        "Evaluate the parametric plot"

        context = context.copy()
        t = np.linspace(extract(self.start.evaluate(context)), extract(self.end.evaluate(context)), 1000)
        z = np.zeros_like(t)
        context.variables[self.var] = t

        return [self.xexpr.evaluate(context) + z, self.yexpr.evaluate(context) + z]
