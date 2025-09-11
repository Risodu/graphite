from pyparsing import *

from xmath import Expression, Constant, Variable, FunCall

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
number = Combine(Optional(Optional(integer) + '.') + integer).setParseAction(lambda toks: Constant(float(toks[0])))
comment = Suppress(Literal('#') + restOfLine)

expression = Forward()

arglist = delimitedList(expression)
functionCall = (identifier + Suppress('(') + arglist + Suppress(')')).setParseAction(lambda toks: FunCall(toks[0], toks[1:])) # type: ignore

atom = functionCall | number | variable
expression <<= infixNotation(atom,
    [
        (oneOf('** ^'), 2, opAssoc.LEFT, parseLeftAssocBinaryOp), # type: ignore
        ('-', 1, opAssoc.RIGHT, lambda toks: FunCall('--', toks[0][1])), # type: ignore
        (oneOf('* /'), 2, opAssoc.LEFT, parseLeftAssocBinaryOp), # type: ignore
        (oneOf('+ -'), 2, opAssoc.LEFT, parseLeftAssocBinaryOp), # type: ignore
    ])            

fundef = Optional(identifier + Optional(Group(Suppress('(') + Optional(arglist) + Suppress(')'))) + Suppress('=')) + expression + Optional(comment)
paramplot = Suppress('(') + Group(arglist) + Suppress(')') + Optional(Suppress('[') + Group(arglist) + Suppress(']')) + Optional(comment)
null = Optional(comment)

def parseFundef(s: str) -> tuple[str, list[Expression], Expression]:
    "Parse the string into function definition, raise `SyntaxError` on error"
    try:
        return fundef.parseString(s, parseAll=True)
    except ParseException:
        raise FatalSyntaxError('Invalid syntax')

def parseParamPlot(s: str) -> list[list[Expression]]:
    "Parse the string into parametric plot definition, raise `SyntaxError` on error"
    try:
        return paramplot.parseString(s, parseAll=True) # type: ignore
    except ParseException:
        raise FatalSyntaxError('Invalid syntax')

def parseNull(s: str) -> None:
    "Parse the string into nothing, raise `SyntaxError` on error"
    try:
        return null.parseString(s, parseAll=True) # type: ignore
    except ParseException:
        raise FatalSyntaxError('Invalid syntax')

if __name__ == '__main__':
    test_string = "-sin(x)+3.14*y-2/z # comment"
    print(fundef.parseString(test_string))