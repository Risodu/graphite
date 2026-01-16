from pyparsing import *
import re

from graphite.xmath import Expression, Scalar, Constant, Variable, FunCall, UserFunction, CompiledLine, FunctionDefinition, EmptyLine, ParamPlot

class FatalSyntaxError(SyntaxError): pass

def parseLeftAssocBinaryOp(toks):
    toks = toks[0]
    result = toks[0]

    for i in range(1, len(toks), 2):
        result = FunCall(toks[i], [result, toks[i + 1]])

    return result

identifier = Word(alphas + '_', alphanums + '_')
variable = identifier.copy().setParseAction(lambda toks: Variable(toks[0]))
integer = Word(nums)
number = Combine(Optional(Optional(integer) + '.') + integer).setParseAction(lambda toks: Constant(Scalar(float(toks[0]))))
comment = Suppress(Literal('//') + restOfLine)

expression = Forward()

arglist = delimitedList(expression)
functionCall = (identifier + Suppress('(') + arglist + Suppress(')')).setParseAction(lambda toks: FunCall(toks[0], toks[1:])) # type: ignore

atom = functionCall | number | variable
expression <<= infixNotation(atom, [
    (oneOf('** ^'), 2, opAssoc.LEFT, parseLeftAssocBinaryOp), # type: ignore
    ('-', 1, opAssoc.RIGHT, lambda toks: FunCall('--', [toks[0][1]])), # type: ignore
    (oneOf('* /'), 2, opAssoc.LEFT, parseLeftAssocBinaryOp), # type: ignore
    (oneOf('+ -'), 2, opAssoc.LEFT, parseLeftAssocBinaryOp), # type: ignore
])

fundef = Optional(identifier + Optional(Group(Suppress('(') + Optional(arglist) + Suppress(')'))) + Suppress('=')) + expression + Optional(comment)
paramplot = Suppress('(') + Group(arglist) + Suppress(')') + Optional(Suppress('[') + Group(arglist) + Suppress(']')) + Optional(comment)
null = Optional(comment)
preprocessKeyword = re.compile(r'(#\w+(=?"(\\"|[^"])+")?)|("(\\"|[^"])+")')

def preprocess(s: str) -> tuple[str, list[str]]:
    "Preprocess the string, filtering out the preprocess keywords"
    kws: list[str] = []
    def repl(m: re.Match[str]):
        kw = m[0]
        kw = kw.strip('#')
        if kw[0] == '"':
            kw = 'label=' + kw
        if '=' not in kw and '"' in kw:
            i = kw.find('"')
            kw = kw[:i] + '=' + kw[i:]
        if '"' in kw:
            kw = kw.replace('="', '=').removesuffix('"')
        kws.append(kw.replace('\\"', '"'))
        return ''
    return preprocessKeyword.sub(repl, s), kws

# FIXME: Type annotation is completely wrong here, possibly also somewhere else 
def parseFundef(s: str) -> tuple[tuple[str, list[Expression], Expression], list[str]]:
    "Parse the string into function definition, raise `SyntaxError` on error"
    s, kws = preprocess(s)
    try:
        return fundef.parseString(s, parseAll=True), kws
    except ParseException:
        raise FatalSyntaxError('Invalid syntax')

def parseParamPlot(s: str) -> tuple[list[list[Expression]], list[str]]:
    "Parse the string into parametric plot definition, raise `SyntaxError` on error"
    s, kws = preprocess(s)
    try:
        return paramplot.parseString(s, parseAll=True), kws  # type: ignore
    except ParseException:
        raise FatalSyntaxError('Invalid syntax')

def parseNull(s: str) -> tuple[None, list[str]]:
    "Parse the string into nothing, raise `SyntaxError` on error"
    s, kws = preprocess(s)
    try:
        null.parseString(s, parseAll=True)
        return None, kws # type: ignore
    except ParseException:
        raise FatalSyntaxError('Invalid syntax')

def compileFunction(line: str) -> tuple[FunctionDefinition, list[str]]:
    toks, kws = parseFundef(line)
    definition = toks[-1]
    name = '' if len(toks) == 1 else toks[0]

    if len(toks) <= 2:
        params = ['theta' if name == 'r' else 'x']

    else:
        if any(not isinstance(v, Variable) for v in toks[1]):
            raise SyntaxError('Function definition parameters must be variable names')
        params = [v.id for v in toks[1]] # type: ignore

    return FunctionDefinition(name, UserFunction(params, definition)), kws

def compileParamPlot(line: str) -> tuple[ParamPlot, list[str]]:
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

def compileNull(line: str) -> tuple[EmptyLine, list[str]]:
    return EmptyLine(), parseNull(line)[1]

def compileLine(line: str) -> tuple[CompiledLine, list[str]]:
    err = None
    for f in [compileFunction, compileParamPlot, compileNull]:
        try:
            return f(line)
        except FatalSyntaxError as e:
            err = e

    raise err # type: ignore
if __name__ == '__main__':
    test_string = "#red #dashed -sin(x)+3.14*y-2/z // comment"
    print(parseFundef(test_string))
