import logging
import re
import sys

from pyjsparser import ast
from pyjsparser.parser import Parser


log = logging.getLogger('bemhtml.compiler')


class CompilerError(Exception):
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
        self.source += "    " * self._indent + line + '\n'


class Compiler(object):
    def __init__(self):
        pass

    def compile(self, js):
        self.functions = []
        self.name_counter = 0
        self.label = None
        self.labels = set()

        program = Parser().parse(js)

        assert isinstance(program, ast.Program)

        preamble = Stream()

        preamble.writeline('# -*- coding: utf-8 -*-')
        preamble.writeline('from pybemhtml.library import *')

        self.stream = Stream()

        self.compile_statements(program.statements, self.stream, program=True)

        for f in self.functions:
            f.writeline('return undefined')

        self.functions.append(self.stream)

        return "\n".join(f.source for f in [preamble] + self.functions)

    def generate_name(self):
        name = 'f%s' % self.name_counter
        self.name_counter += 1
        return name

    def optimize_expression(self, expr):
        pass

    def compile_assignment(self, lvalue, *args):
        if isinstance(lvalue, ast.Identifier):
            return ("scope.__setitem__(%s, %s)") % ((repr(lvalue.name),) + args)
        elif isinstance(lvalue, ast.PropertyAccessor):
            node = self.compile_expression(lvalue.node)
            if isinstance(lvalue, ast.BracketAccessor):
                element = self.compile_expression(lvalue.element)
            elif isinstance(lvalue, ast.DotAccessor):
                assert isinstance(lvalue.element, ast.Identifier)
                element = repr(lvalue.element.name)
            return "setproperty(%s, %s, %s)" % ((node, element) + args)
        else:
            raise CompilerError("Cannot assign to %r" % lvalue)

    def compile_update(self, lvalue, function, postfix, *args):
        if isinstance(lvalue, ast.Identifier):
            return "scope.update(%s, %s, postfix=%s)" % (repr(lvalue.name), function, 'True' if postfix else 'False')
        elif isinstance(lvalue, ast.PropertyAccessor):
            node = self.compile_expression(lvalue.node)
            if isinstance(lvalue, ast.BracketAccessor):
                element = self.compile_expression(lvalue.element)
            elif isinstance(lvalue, ast.DotAccessor):
                assert isinstance(lvalue.element, ast.Identifier)
                element = repr(lvalue.element.name)
            return "updateproperty(%s, %s, %s, postfix=%s)" % (node, element, function, 'True' if postfix else 'False')
        else:
            raise CompilerError("Cannot assign to %r" % lvalue)

    def compile_delete(self, object):
        if isinstance(object, ast.Identifier):
            return "scope.delete(%r)" % object.name
        elif isinstance(object, ast.PropertyAccessor):
            node = self.compile_expression(object.node)
            if isinstance(object, ast.BracketAccessor):
                element = self.compile_expression(object.element)
            elif isinstance(object, ast.DotAccessor):
                assert isinstance(object.element, ast.Identifier)
                element = repr(object.element.name)
            return "deleteproperty(%s, %s)" % (node, element)
        else:
            raise CompilerError("Cannot delete %r" % object)

    def compile_function(self, expr):
        for p in expr.parameters or []:
            assert isinstance(p, ast.Identifier)

        name = 'function'

        if expr.node:
            assert isinstance(expr.node, ast.Identifier)
            name = expr.node.name

        parameters = [repr(p.name) for p in expr.parameters or []]

        if name:
            return "Function(%s,[%s],scope,%r)" % (self.compile_statements(expr.statements), ','.join(parameters), name)        
        else:
            return "Function(%s,[%s],scope)" % (name, self.compile_statements(expr.statements), ','.join(parameters))     

    def compile_expression(self, expr):
        if isinstance(expr, list):
            assert len(expr) == 1
            return self.compile_expression(expr[0])

        if isinstance(expr, ast.FuncDecl):
            compiled = self.compile_function(expr)
            
            if expr.node:
                return self.compile_assignment(expr.node, compiled)

            return compiled
                
        if isinstance(expr, ast.UnaryOp):
            operator = expr.operator

            if operator == '!':
                operator = 'not'

            if operator == '--':
                return self.compile_update(expr.value, "decr", postfix=expr.postfix)

            if operator == '++':
                return self.compile_update(expr.value, "incr", postfix=expr.postfix)

            if operator == 'delete':
                return self.compile_delete(expr.value)

            return "(%s(%s))" % (operator, self.compile_expression(expr.value))

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

            # Javascript coercion to string
            if operator == '+':
                if isinstance(expr.left, ast.String):
                    return '%s + unicode(%s)' % (self.compile_string(expr.left), self.compile_expression(expr.right))
                if isinstance(expr.right, ast.String):
                    return 'unicode(%s) + %s' % (self.compile_expression(expr.left), self.compile_string(expr.right))

            return "(%s %s %s)" % (self.compile_expression(expr.left), operator, self.compile_expression(expr.right))

        if isinstance(expr, ast.Assign):
            return self.compile_assignment(expr.node, self.compile_expression(expr.expr))

        if isinstance(expr, ast.FuncCall):
            args = map(self.compile_expression, expr.arguments or [])

            if isinstance(expr.node, ast.PropertyAccessor):
                instance = self.compile_expression(expr.node.node)
            else:
                instance = 'undefined'

            return "%s(%s,[%s])" % (self.compile_expression(expr.node), instance, ",".join(args))

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
            assert isinstance(expr.item, ast.Identifier)
            
            return 'forinloop(this,scope,%r,%s,%s)' % (expr.item.name, self.compile_expression(expr.iterator), self.compile_statements([expr.statement]))

        if isinstance(expr, ast.While):
            return 'whileloop(this,scope,lambda scope:%s,%s)' % (self.compile_expression(expr.condition), self.compile_statements([expr.statement]))

        if isinstance(expr, ast.New):
            return 'new(%s,[%s])' % (self.compile_expression(expr.identifier), ','.join(self.compile_expression(arg) for arg in expr.arguments))

        if isinstance(expr, ast.Number):
            return '%s' % expr.value

        if isinstance(expr, ast.BracketAccessor):
            return 'getproperty(%s,%s)' % (self.compile_expression(expr.node), self.compile_expression(expr.element))

        if isinstance(expr, ast.DotAccessor):
            assert isinstance(expr.element, ast.Identifier)
            return 'getproperty(%s,%r)' % (self.compile_expression(expr.node), expr.element.name)

        if isinstance(expr, ast.String):
            return self.compile_string(expr)

        if isinstance(expr, ast.Identifier):
            if expr.name == 'undefined':
                return 'undefined'

            return "scope[%r]" % expr.name

        if isinstance(expr, ast.Array):
            return "[%s]" % ','.join(map(self.compile_expression, expr.items or []))

        if expr == 'this':
            return "this"

        if expr is None:
            return 'undefined'

        raise Exception("Unexpected node %r" % expr)

    UNESCAPE = re.compile(r'\\(u[0-9a-f]{4}|.)', re.U)

    def compile_string(self, string):
        # Unescaping and then escaping to be safe
        def replacement(match):
            text = match.group(1)

            if text[0] == 'u':
                return unichr(int(text[1:], 16))

            if text[0] == 'n':
                return '\n'

            if text[0] in ["'", '"', '\\']:
                return text

            raise CompilerError("Unknown escaped character \\%s" % text)

        return repr(self.UNESCAPE.sub(replacement, string.data[1:-1]))

    def compile_statements(self, statements, stream=None, program=False, label=None):
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

        assert isinstance(statements, list)

        for statement in statements:
            self.compile_statement(statement, stream, program)

        if name:
            if label:
                stream.writeline('return Label(%r)' % label)
            else:
                stream.writeline('return undefined')

        return name

    def compile_statement(self, statement, stream=None, program=False):
        if statement is None:
            return

        if isinstance(statement, list):
            self.compile_statements(statement, stream)
            return

        if isinstance(statement, ast.VariableDeclaration):
            # TODO: declaring variable affects whole scope, even if declaration is not executed
            assert isinstance(statement.node, ast.Identifier)

            stream.writeline('scope.var(%s,%s)' % (repr(statement.node.name), self.compile_expression(statement.expr)))
            return

        if isinstance(statement, ast.If):
            expression = self.compile_expression(statement.expr)

            stream.writeline('if %s:' % expression)

            stream.indent()
            self.compile_statement(statement.true, stream)
            stream.dedent()

            if statement.false:
                stream.writeline('else:')
                stream.indent()
                self.compile_statement(statement.false, stream)
                stream.dedent()

            return

        if isinstance(statement, ast.Assign):
            stream.writeline(self.compile_assignment(statement.node, self.compile_expression(statement.expr)))
            return

        if isinstance(statement, ast.FuncDecl):
            if statement.node:
                stream.writeline(self.compile_assignment(statement.node, self.compile_function(statement)))
                return

        if isinstance(statement, ast.LabelledStatement):
            assert isinstance(statement.identifier, ast.Identifier)
            
            assert statement.identifier.name not in self.labels

            self.labels.add(statement.identifier.name)

            label_name = self.compile_statements(statement.statement, label=statement.identifier.name)
            
            stream.writeline('label = %s(this, scope)' % label_name)
            stream.writeline('if not isinstance(label, Label) or label != %r:' % (statement.identifier.name))
            stream.indent()
            
            if not program:
                stream.writeline('return label')
            else:
                stream.writeline('assert False')
            
            stream.dedent()

            self.labels.remove(statement.identifier.name)
            
            return

        if isinstance(statement, ast.Break):
            assert isinstance(statement.identifier, ast.Identifier)
            assert statement.identifier.name in self.labels
            stream.writeline('return Label(%r)' % statement.identifier.name)
            return

        # assert, for testing
        if isinstance(statement, ast.FuncCall):
            if isinstance(statement.node, ast.Identifier) and statement.node.name == 'assert':
                stream.writeline('assert %s' % self.compile_expression(statement.arguments))
                return

        if isinstance(statement, ast.Return):
            stream.writeline('return %s' % self.compile_expression(statement.expression))
            return

        stream.writeline(self.compile_expression(statement))

        return
