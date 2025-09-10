from pyparsing import *

def namer(name):
    return lambda s, loc, toks: (name, toks[0], loc)

# --- Token definitions ---
integer = Word(nums)
number = Combine(Optional(Optional(integer) + '.') + integer).setParseAction(namer("constant"))
identifier = Word(alphas + '_', alphanums + '_').setParseAction(namer("identifier"))
operator = oneOf("+ - * / ** ^ ( ) = ,").setParseAction(namer("operator"))
other = Regex(r"." ).setParseAction(namer("other"))

# --- Assemble tokenizer ---
token = number | identifier | operator | other
token.ignore(White(" \t"))

tokenizer = OneOrMore(token)

def tokenize(code: str) -> list[tuple[str, str, int]]:
    return tokenizer.parseString(code)

if __name__ == "__main__":
    test_string = "sin(x)+3.14*y-2/z"
    for tok in tokenizer.parseString(test_string):
        print(tok)