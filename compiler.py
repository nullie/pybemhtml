import re
import sys

sys.path.append('../pyjsparser')

from pyjsparser import ast
from pyjsparser.parser import Parser


class Stream(object):
    def __init__(self):
        self._indent = 0
        self.source = ""
        self.lineno = 0

    def indent(self):
        self._indent += 1

    def dedent(self):
        self._indent -= 1

        if self._indent < 0:
            raise Exception("Unexpected dedent")

    def writeline(self, line):
        self.source += " " * self._indent + line + '\n'
        self.lineno += 1


def optimize_expression(expr):
    pass


def compile_expression(expr):
    if isinstance(expr, list):
        assert len(expr) == 1
        expr = expr[0]

    if isinstance(expr, ast.UnaryOp):
        return "%s %s" % (expr.operator, compile_expression(expr.value))

    if isinstance(expr, ast.BinOp):
        return "(%s %s %s)" % (compile_expression(expr.left), expr.operator, compile_expression(expr.right))

    if isinstance(expr, ast.FuncCall):
        return "%s(%s)" % (compile_expression(expr.node), ",".join(map(compile_expression, expr.arguments)))

    if isinstance(expr, ast.Boolean):
        if expr.value == 'true':
            return 'True'
        elif expr.value == 'false':
            return 'False'
        else:
            assert False

    if isinstance(expr, ast.PropertyAccessor):
        return '%s[%s]' % (compile_expression(expr.node), compile_expression(expr.element))

    if isinstance(expr, ast.String):
        return repr(expr.data[1:-1])

    if isinstance(expr, ast.Identifier):
        return repr(expr.name)

    if isinstance(expr, str):
        if expr == 'this':
            return 'this'

    return repr(expr)

LETTER_OR_DIGIT = re.compile('[a-zA-Z0-9]')
LETTER = re.compile('[a-zA-Z]')

def escape_identifier(name):
    letters = []

    if not LETTER.match(name[0]):
        letters.append('_')
        
    for letter in name:
        if not LETTER_OR_DIGIT.match(letter):
            letters.append('_%x' % ord(letter))
        else:
            letters.append(letter)

    return ''.join(letters)


def compile(program):
    assert isinstance(program, ast.Program)

    stream = Stream()

    for statement in program.statements:
        if isinstance(statement, list):
            assert len(statement) == 1
            statement = statement[0]

        if isinstance(statement, ast.VariableDeclaration):
            assert isinstance(statement.node, ast.Identifier)

            stream.writeline('%s = %s' % (escape_identifier(statement.node.name), compile_expression(statement.expr)))
            continue

        if isinstance(statement, ast.If):
            assert len(statement.expr) == 1
            expression = compile_expression(statement.expr[0])

            stream.writeline('if %s:' % expression)

            stream.writeline(repr(statement.true))
            stream.writeline(repr(statement.false))

            stream.indent()
            stream.writeline('pass')
            stream.dedent()
            continue

        raise Exception("Unexpected statement %r" % statement)
            
    return stream


js = open('page1.bemhtml.js').read()

parser = Parser()

result = compile(parser.parse(js))

print result.source
print result.lineno, 'lines'
