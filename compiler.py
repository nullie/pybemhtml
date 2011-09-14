import re
import sys

sys.path.append('../pyjsparser')

from pyjsparser import ast
from pyjsparser.parser import Parser

CONTEXT = ['Object', 'Array', 'Boolean', 'Number', 'Function', 'String', 'true', 'false', 'NaN', 'scope']

class CompileError(Exception):
    pass


class Stream(object):
    def __init__(self):
        self._indent = 0
        self.source = ""

    def child(self):
        c = Stream()
        c._indent = self._indent
        return c

    def indent(self):
        self._indent += 1

    def dedent(self, n=1):
        self._indent -= n

        if self._indent < 0:
            raise Exception("Unexpected dedent")

    def write(self, source):
        self.source += source

    def writeline(self, line):
        self.source += " " * self._indent + line + '\n'


class Compiler(object):
    def __init__(self):
        pass

    def compile(self, js):
        self.functions = []
        self.name_counter = 0

        program = Parser().parse(js)

        assert isinstance(program, ast.Program)

        self.stream = Stream()

        self.stream.writeline('from lib import *')

        self.stream.writeline('def program():')

        self.stream.indent()

        self.stream.writeline('context=init()')

        for name in CONTEXT:
            self.stream.writeline("%s=context['%s']" % (name, name))

        program_stream = self.stream.child()

        self.compile_statements(program.statements, program_stream, in_function=False)

        for f in self.functions:
            f.writeline('return undefined')

        self.stream.write("".join(f.source for f in self.functions))

        self.stream.write(program_stream.source)

        self.stream.writeline('return scope')

        return self.stream.source

    def generate_name(self):
        name = 'f%s' % self.name_counter
        self.name_counter += 1
        return name

    def optimize_expression(self, expr):
        pass

    def compile_assignment(self, lvalue, operator, *args):
        if isinstance(lvalue, ast.Identifier):
            return ("scope" + operator) % ((repr(lvalue.name),) + args)
        elif isinstance(lvalue, ast.PropertyAccessor):
            return ("%s"+ operator) % ((self.compile_expression(lvalue.node), self.compile_expression(lvalue.element)) + args)
        else:
            raise CompileError("Cannot assign %r" % expr)

    def compile_function(self, expr):
        for p in expr.parameters or []:
            assert isinstance(p, ast.Identifier)

        parameters = [repr(p.name) for p in expr.parameters or []]

        return "Function(%s,[%s],scope)" % (self.compile_statements(expr.statements), ','.join(parameters))        

    def compile_expression(self, expr):
        if isinstance(expr, list):
            assert len(expr) == 1
            return self.compile_expression(expr[0])

        if isinstance(expr, ast.FuncDecl):
            compiled = self.compile_function(expr)
            
            if expr.node:
                return self.compile_assignment(expr.node, '.__setitem__(%s,%s)', compiled)

            return compiled
                
        if isinstance(expr, ast.UnaryOp):
            operator = expr.operator

            if operator == '!':
                operator = 'not'

            if operator == '--':
                return self.compile_assignment(expr.value, ".postfixincr(%s,-1)" if expr.postfix else '.prefixincr(%s,-1)')

            if operator == '++':
                return self.compile_assignment(expr.value, ".postfixincr(%s,1)" if expr.postfix else '.prefixincr(%s,1)')

            return "%s(%s)" % (operator, self.compile_expression(expr.value))

        if isinstance(expr, ast.BinOp):
            operator = expr.operator

            if operator == '===': # hack
                operator = '=='

            if operator == '!==':
                operator = '!='
            
            if operator == '&&':
                operator = 'and'

            if operator == '||':
                operator = 'or'

            return "(%s %s %s)" % (self.compile_expression(expr.left), operator, self.compile_expression(expr.right))

        if isinstance(expr, ast.Assign):
            return self.compile_assignment(expr.node, '.__setitem__(%s, %s)', self.compile_expression(expr.expr))

        if isinstance(expr, ast.FuncCall):
            args = map(self.compile_expression, expr.arguments or [])

            if isinstance(expr.node, ast.PropertyAccessor):
                instance = self.compile_expression(expr.node.node)
            else:
                instance = 'undefined'

            return "%s(%s,Array([%s]))" % (self.compile_expression(expr.node), instance, ",".join(args))

        if isinstance(expr, ast.Object):
            properties = []
            for assignment in expr.properties:
                assert isinstance(assignment, ast.Assign) and assignment.operator == ':'

                if isinstance(assignment.node, ast.Identifier):
                    key = unicode(assignment.node.name)
                elif isinstance(assignment.node, ast.String):
                    key = unicode(assignment.node.data[1:-1])
                elif isinstance(assignment.node, ast.Number):
                    key = unicode(assignment.node.value)
                else:
                    assert False
                
                properties.append("%r:%s" % (key, self.compile_expression(assignment.expr)))
                
            return "Object({%s})" % ",".join(properties)

        if isinstance(expr, ast.Boolean):
            if expr.value == 'true':
                return 'true'
            elif expr.value == 'false':
                return 'false'
            else:
                assert False

        if isinstance(expr, ast.If):
            return '(%s if %s else %s)' % (self.compile_expression(expr.true), self.compile_expression(expr.expr), self.compile_expression(expr.false))

        if isinstance(expr, ast.ForIn):
            assert isinstance(expr.item, ast.Identifier)
            
            return 'forinloop(scope,lambda scope:%s,%s)' % (self.compile_expression(expr.iterator), self.compile_statements(expr.statement))

        if isinstance(expr, ast.While):
            return 'whileloop(scope,lambda scope:%s,%s)' % (self.compile_expression(expr.condition), self.compile_statements(expr.statement))

        if isinstance(expr, ast.New):
            return 'new(%s,Array([%s]))' % (self.compile_expression(expr.identifier), ','.join(self.compile_expression(arg) for arg in expr.arguments))

        if isinstance(expr, ast.Number):
            return 'Number(%s)' % expr.value

        if isinstance(expr, ast.BracketAccessor):
            return '%s[%s]' % (self.compile_expression(expr.node), self.compile_expression(expr.element))

        if isinstance(expr, ast.DotAccessor):
            assert isinstance(expr.element, ast.Identifier)
            return '%s[%r]' % (self.compile_expression(expr.node), expr.element.name)

        if isinstance(expr, ast.String):
            return 'String(%r)' % expr.data[1:-1]

        if isinstance(expr, ast.Identifier):
            if expr.name == 'undefined':
                return 'undefined'

            return "scope[%r]" % expr.name

        if isinstance(expr, ast.Array):
            return "Array([%s])" % ','.join(map(self.compile_expression, expr.items or []))

        if isinstance(expr, str):
            if expr == 'this':
                return "this"

        if expr is None:
            return 'undefined'

        raise Exception("Unexpected node %r" % expr)

    def compile_statements(self, statements, stream=None, in_function=True):
        if not stream:
            name = self.generate_name()
            stream = self.stream.child()
            self.functions.append(stream)
            stream.writeline('def %s(this,scope):' % name)
            stream.indent()
        else:
            name = None

        if statements is None:
            return name

        for statement in statements:
            if statement is None:
                continue

            if isinstance(statement, list):
                self.compile_statements(statement, stream)
                continue

            if isinstance(statement, ast.VariableDeclaration):
                assert isinstance(statement.node, ast.Identifier)

                stream.writeline('scope.var(%s,%s)' % (repr(statement.node.name), self.compile_expression(statement.expr)))
                continue

            if isinstance(statement, ast.If):
                expression = self.compile_expression(statement.expr)

                stream.writeline('if %s:' % expression)
                stream.indent()
                self.compile_statements(statement.true, stream)
                stream.dedent()

                if statement.false:
                    stream.writeline('else:')
                    stream.indent()
                    self.compile_statements(statement.false, stream)
                    stream.dedent()

                continue

            if isinstance(statement, ast.Assign):
                stream.writeline(self.compile_assignment(statement.node, "[%s]=%s", self.compile_expression(statement.expr)))
                continue

            if isinstance(statement, ast.FuncDecl):
                if statement.node:
                    stream.writeline(self.compile_assignment(statement.node, "[%s]=%s", self.compile_function(statement)))
                    continue

            if isinstance(statement, ast.Return):
                assert in_function

                stream.writeline('return %s' % self.compile_expression(statement.expression))
                continue

            stream.writeline(self.compile_expression(statement))

        return name


if __name__ == '__main__':
    js = open('test.js').read()

    result = Compiler().compile(js)

    print result

    exec(result)

    scope = program()
    print scope['foo'](scope['foo'], scope['Array']([]))
