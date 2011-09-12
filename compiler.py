import re
import sys

sys.path.append('../pyjsparser')

from pyjsparser import ast
from pyjsparser.parser import Parser


PREAMBLE = """
def foo():
    pass
"""


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


class Compiler(object):
    def __init__(self):
        pass

    def compile(self, program):
        self.code = Stream()
        self.name_counter = 0

        assert isinstance(program, ast.Program)

        for line in PREAMBLE.strip().split('\n'):
            self.code.writeline(line)

        self.compile_statements(program.statements)

        return self.code

    def generate_name(self):
        name = '_pybemhtml_%s' % self.name_counter
        self.name_counter += 1
        return name

    def optimize_expression(self, expr):
        pass

    def compile_expression(self, expr):
        if isinstance(expr, list):
            assert len(expr) == 1
            return self.compile_expression(expr[0])

        if isinstance(expr, ast.FuncDecl):
            name = self.generate_name()
            
            self.code.writeline('def %s(%s):' % (name, ','.join(map(self.compile_expression, expr.parameters or []))))
            self.code.indent()
            self.compile_statements(expr.statements)
            self.code.dedent()
            return name

        if isinstance(expr, ast.UnaryOp):
            operator = expr.operator

            if operator == '!':
                operator = 'not'

            return "%s (%s)" % (operator, self.compile_expression(expr.value))

        if isinstance(expr, ast.BinOp):
            operator = expr.operator

            if operator == '===':
                operator = '=='
            
            if operator == '&&':
                operator = 'and'

            if operator == '||':
                operator = 'or'

            return "(%s %s %s)" % (self.compile_expression(expr.left), operator, self.compile_expression(expr.right))

        if isinstance(expr, ast.Assign):
            return "(%s %s %s)" % (self.compile_expression(expr.node), expr.operator, self.compile_expression(expr.expr))

        if isinstance(expr, ast.FuncCall):
            return "%s(%s)" % (self.compile_expression(expr.node), ",".join(map(self.compile_expression, expr.arguments or [])))

        if isinstance(expr, ast.Object):
            properties = []
            for assignment in expr.properties:
                assert isinstance(assignment, ast.Assign) and assignment.operator == ':'
                properties.append("%s: %s" % (self.compile_expression(assignment.node), self.compile_expression(assignment.expr)))
                
            return "{%s}" % ",".join(properties)

        if isinstance(expr, ast.Boolean):
            if expr.value == 'true':
                return 'True'
            elif expr.value == 'false':
                return 'False'
            else:
                assert False

        if isinstance(expr, ast.If):
            return '(%s if %s else %s)' % (self.compile_expression(expr.true), self.compile_expression(expr.expr), self.compile_expression(expr.false))

        if isinstance(expr, ast.ForIn):
            name = self.generate_name

            self.code.writeline('for %s in %s:' % (expr.item, self.compile_expression(expr.iterator)))
            self.code.indent()
            self.compile_statements(expr.statement)
            self.code.dedent()
            return ''

        if isinstance(expr, ast.While):
            name = self.generate_name
            self.code.writeline('while %s:' % self.compile_expression(expr.condition))
            self.code.indent()
            self.compile_statements(expr.statement)
            self.code.dedent()
            return ''

        if isinstance(expr, ast.While):
            pass

        if isinstance(expr, ast.Number):
            return expr.value

        if isinstance(expr, ast.PropertyAccessor):
            return '%s[%s]' % (self.compile_expression(expr.node), self.compile_expression(expr.element))

        if isinstance(expr, ast.String):
            return repr(expr.data[1:-1])

        if isinstance(expr, ast.Identifier):
            return expr.name

        if isinstance(expr, ast.Array):
            return "[%s]" % ','.join(map(self.compile_expression, expr.items or []))

        if isinstance(expr, str):
            return expr

        if expr is None:
            return ''

        raise Exception("Unexpected node %r" % expr)

    LETTER_OR_DIGIT = re.compile('[a-zA-Z0-9_]')
    LETTER = re.compile('[a-zA-Z_]')

    def escape_identifier(self, name):
        letters = []

        if not self.LETTER.match(name[0]):
            letters.append('_')

        for letter in name:
            if not self.LETTER_OR_DIGIT.match(letter):
                letters.append('_%x' % ord(letter))
            else:
                letters.append(letter)

        return ''.join(letters)

    def compile_statements(self, statements):
        for statement in statements:
            if statement is None:
                continue

            if isinstance(statement, list):
                self.compile_statements(statement)
                continue

            if isinstance(statement, ast.VariableDeclaration):
                assert isinstance(statement.node, ast.Identifier)

                self.code.writeline('%s = %s' % (self.escape_identifier(statement.node.name), self.compile_expression(statement.expr)))
                continue

            if isinstance(statement, ast.If):
                expression = self.compile_expression(statement.expr)

                self.code.writeline('if %s:' % expression)
                self.code.indent()
                self.compile_statements(statement.true)
                self.code.dedent()

                if statement.false:
                    self.code.writeline('else:')
                    self.code.indent()
                    self.compile_statements(statement.false)
                    self.code.dedent()

                continue

            if isinstance(statement, ast.Return):
                self.code.writeline('return %s' % self.compile_expression(statement.expression))
                continue

            self.code.writeline(self.compile_expression(statement))
            
            continue

            raise Exception("Unexpected statement %r" % statement)


js = open('page1.bemhtml.js').read()

parser = Parser()

result = Compiler().compile(parser.parse(js))

print result.source
