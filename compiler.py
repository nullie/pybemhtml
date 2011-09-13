import re
import sys

sys.path.append('../pyjsparser')

from pyjsparser import ast
from pyjsparser.parser import Parser


PREAMBLE = """
from compiler import *
scope=RootScope()
"""

class Undefined(object):
    def __getitem__(self, *args):
        raise TypeError('undefined has no properties')

    def __str__(self):
        return 'undefined'

    __setitem__ = __getitem__


undefined = Undefined()


class Object(dict):
    def __init__(self, *args, **kwargs):
        super(Object, self).__init__(*args, **kwargs)

    def __getitem__(self, item):
        try:
            return super(Object, self).__getitem__(unicode(item))
        except (KeyError, TypeError):
            return undefined

    def __setitem__(self, item, value):
        return super(Object, self).__setitem__(unicode(item), value)

    def __eq__(self, other):
        return False


class Array(list):
    def __init__(self, items):
        super(Array, self).__init__(items)

    def __getitem__(self, item):
        try:
            return super(Array, self).__getitem__(item)
        except (TypeError, IndexError):
            return undefined


class Function(object):
    def __init__(self, scope, parameters, code):
        self.scope = scope
        self.parameters = parameters
        self.code = code

    def __call__(self, *args):
        return self.apply(args=args)

    def apply(self, this=undefined, args=Array([])):
        scope = Scope(self.scope)

        scope.var('this', this)
        scope.var('arguments', args)

        for i, p in enumerate(self.parameters):
            scope.var(p, args[i])

        return self.code(scope)


class ReferenceError(Exception):
    pass


class RootScope(object):
    def __init__(self):
        self.variables = {}

    def __getitem__(self, item):
        try:
            return self.variables[item]
        except KeyError:
            raise ReferenceError('%s is not defined' % item)

    def __setitem__(self, item, value):
        self.variables[item] = value
        return value

    def prefixincr(self, item, increment):
        value = self[item] + increment
        self[item] = value
        return value

    def postfixincr(self, item, increment):
        value = self[item]
        self[item] = value + increment
        return value
    

    def var(self, name, value):
        self.variables[name] = value


class Scope(RootScope):
    def __init__(self, parent=RootScope()):
        self.parent = parent
        super(Scope, self).__init__()

    def __getitem__(self, item):
        try:
            return self.variables[item]
        except KeyError:
            return self.parent[item]

    def __setitem__(self, item, value):
        if item in self.variables:
            self.variables[item] = value
        else:
            self.parent[item] = value

        return value

class String(unicode):
    def __add__(self, other):
        if not isinstance(other, String):
            return self + String(other)

        return unicode.__add__(self, other)

def forinloop(scope, item, iterator, statement):
    scope = Scope(scope)

    for value in iterator:
        scope.var(item, value)
        
        statement(scope)


def whileloop(scope, condition, statement):
    scope = Scope(scope)

    while condition(scope):
        statement(scope)


def wrap(json):
    if isinstance(json, dict):
        return Object((wrap(key), wrap(value)) for key, value in json.items())

    if isinstance(json, list):
        return Array(wrap(json) for json in json)

    if isinstance(json, str):
        return String(json)

    if isinstance(json, int):
        return json

    if isinstance(json, float):
        return json

    raise TypeError("Unknown JSON type %r" % json)

class CompileError(Exception):
    pass


class Stream(object):
    def __init__(self):
        self._indent = 0
        self.source = ""
        self.lineno = 0

    def indent(self):
        self._indent += 1

    def dedent(self, n=1):
        self._indent -= n

        if self._indent < 0:
            raise Exception("Unexpected dedent")

    def writeline(self, line):
        self.source += " " * self._indent + line + '\n'
        self.lineno += 1


class Compiler(object):
    def __init__(self):
        pass

    def compile(self, js):
        self.functions = []
        self.name_counter = 0

        program = Parser().parse(js)

        assert isinstance(program, ast.Program)

        stream = Stream()

        for line in PREAMBLE.strip().split('\n'):
            stream.writeline(line)

        self.compile_statements(program.statements, stream)

        for f in self.functions:
            f.writeline('return undefined')

        self.functions.append(stream)

        return "".join(f.source for f in self.functions)

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

    def compile_expression(self, expr):
        if isinstance(expr, list):
            assert len(expr) == 1
            return self.compile_expression(expr[0])

        if isinstance(expr, ast.FuncDecl):
            for p in expr.parameters or []:
                assert isinstance(p, ast.Identifier)

            parameters = [repr(p.name) for p in expr.parameters or []]

            return "Function(scope,[%s],%s)" % (','.join(parameters), self.compile_statements(expr.statements))

        if isinstance(expr, ast.UnaryOp):
            operator = expr.operator

            if operator == '!':
                operator = 'not'

            if operator == '--':
                return self.compile_assignment(expr.value, ".postfixincr(%s,-1)" if expr.postfix else '.prefixincr(%s,-1)')

            if operator == '++':
                return self.compile_assignment(expr.value, ".postfixincr(%s,1)" if expr.postfix else '.prefixincr(%s,1)')

            return "%s (%s)" % (operator, self.compile_expression(expr.value))

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
            return "%s(%s)" % (self.compile_expression(expr.node), ",".join(map(self.compile_expression, expr.arguments or [])))

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
                
                properties.append("(%r,%s)" % (key, self.compile_expression(assignment.expr)))
                
            return "Object([%s])" % ",".join(properties)

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
            assert isinstance(expr.item, ast.Identifier)
            
            return 'forinloop(scope,lambda scope:%s,%s)' % (self.compile_expression(expr.iterator), self.compile_statements(expr.statement))

        if isinstance(expr, ast.While):
            return 'whileloop(scope,lambda scope:%s,%s)' % (self.compile_expression(expr.condition), self.compile_statements(expr.statement))

        if isinstance(expr, ast.New):
            return 'new(%s, [%s])' % (self.compile_expression(expr.identifier), ','.join(self.compile_expression(arg) for arg in expr.arguments))

        if isinstance(expr, ast.Number):
            return expr.value

        if isinstance(expr, ast.BracketAccessor):
            return '%s[%s]' % (self.compile_expression(expr.node), self.compile_expression(expr.element))

        if isinstance(expr, ast.DotAccessor):
            assert isinstance(expr.element, ast.Identifier)
            return '%s[%r]' % (self.compile_expression(expr.node), expr.element.name)

        if isinstance(expr, ast.String):
            return 'String(%r)' % expr.data[1:-1]

        if isinstance(expr, ast.Identifier):
            return "scope[%r]" % expr.name

        if isinstance(expr, ast.Array):
            return "Array([%s])" % ','.join(map(self.compile_expression, expr.items or []))

        if isinstance(expr, str):
            if expr == 'this':
                return "scope['this']"

        if expr is None:
            return 'undefined'

        raise Exception("Unexpected node %r" % expr)

    def compile_statements(self, statements, stream=None):
        if not stream:
            name = self.generate_name()
            stream = Stream()
            self.functions.append(stream)
            stream.writeline('def %s(scope):' % name)
            stream.indent()
        else:
            name = None

        for statement in statements:
            if statement is None:
                continue

            if isinstance(statement, list):
                self.compile_statements(statement, stream)
                continue

            if isinstance(statement, ast.VariableDeclaration):
                assert isinstance(statement.node, ast.Identifier)

                stream.writeline('scope.var(%s, %s)' % (repr(statement.node.name), self.compile_expression(statement.expr)))
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

            if isinstance(statement, ast.Return):
                stream.writeline('return %s' % self.compile_expression(statement.expression))
                continue

            stream.writeline(self.compile_expression(statement))

        #stream.writeline('return undefined')
            
        return name


if __name__ == '__main__':
    js = open('test.js').read()

    result = Compiler().compile(js)

    print result
