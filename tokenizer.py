from pyparsing import *

def namer(name):
    return lambda s, loc, toks: (name, toks[0], loc)

# --- Token definitions ---
integer = Word(nums)
number = Combine(Optional(Optional(integer) + '.') + integer).setParseAction(namer("number"))
identifier = Word(alphas + '_', alphanums + '_').setParseAction(namer("identifier"))
operator = oneOf("+ - * / ** ^ = ,").setParseAction(namer("operator"))
comment = Combine(Literal('//') + restOfLine).setParseAction(namer("comment")) # type: ignore
preprocess = Combine(Literal('#') + Word(alphanums)).setParseAction(namer("preprocess"))
other = Regex(r"." ).setParseAction(namer("other"))

# --- Assemble tokenizer ---
token = comment | preprocess | number | identifier | operator | other
token.ignore(White(" \t"))

tokenizer = OneOrMore(token)

def tokenize(code: str) -> list[tuple[str, str, int]]:
    return tokenizer.parseString(code)

if __name__ == "__main__":
    test_string = "sin(x)+3.14*y-2/z #red #dashed // comment"
    for tok in tokenizer.parseString(test_string):
        print(tok)
