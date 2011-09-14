# Javascript objects

class javascript_object(type):
    def __new__(mcs, name, bases, dict):
        prototype = {}

        for key, value in dict.items():
            if hasattr(value, 'js'):
                prototype[key] = dict.pop(key)

        klass = type.__new__(mcs, name, bases, dict)

        base = klass if name == 'Object' else bases[0]

        klass.prototype = base(prototype, prototype=getattr(klass, 'prototype', None))

        return klass


def javascript(method):
    method.js = True
    return method


class ReferenceError(Exception):
    pass


class Scope(object):
    def __init__(self, parent=None):
        self.variables = {}
        self.parent = parent
        super(Scope, self).__init__()

    def __getitem__(self, item):
        if item == 'undefined':
            return undefined

        try:
            return self.variables[item]
        except KeyError:
            if self.parent:
                return self.parent[item]
            else:
                raise ReferenceError('%s is not defined' % item)

    def var(self, item, value):
           self.variables[item] = value     

    def __setitem__(self, item, value):
        if item in self.variables or not self.parent:
            self.variables[item] = value
        else:
            self.parent[item] = value

        return value

    def __repr__(self):
        return repr(self.variables)


def typeof(value):
    if isinstance(value, Object):
        return 'object'

    if isinstance(value, String):
        return 'string'

    if isinstance(value, Number):
        return 'number'

    if value is undefined:
        return 'undefined'

    assert False


def forinloop(scope, item, iterator, statement):
    scope = Scope(scope)

    for value in iterator:
        scope.var(item, value)
        
        statement(scope)

    return undefined


def new(function, arguments):
    this = Object(prototype=function['prototype'])
    function(this, arguments)
    return this
    

def whileloop(scope, condition, statement):
    scope = Scope(scope)

    while condition(scope):
        statement(scope)

    return undefined


def function(this, arguments):
    raise NotImplementedError('Function is not implemented')


def regexp(this, arguments):
    raise NotImplementedError('RegExp is not implemented')


def array(this, arguments):
    if len(arguments) == 1 and isinstance(arguments[0], int):
        return Array([undefined] * arguments[0])
    
    return Array(arguments)


class UndefinedType(object):
    def __getitem__(self, item):
        raise TypeError('undefined has no properties')

    def __str__(self):
        return 'undefined'

    def __repr__(self):
        return 'undefined'

    def __call__(self, this, arguments):
        raise TypeError('undefined is not a function')

    def __add__(self, other):
        if isinstance(other, int):
            return NaN

    def __nonzero__(self):
        return False

    __setitem__ = __getitem__

undefined = UndefinedType()

del UndefinedType


def init():
    class Object(dict):
        __metaclass__ = javascript_object

        def __init__(self, value={}, prototype=None):
            dict.__init__(self, value)

        @javascript
        def hasOwnProperty(this, arguments): 
            prop = arguments[0]

            return prop in this

        @javascript
        def toString(this, arguments):
            return '[object %s]' % this.__class__.__name__

        def __getitem__(self, item):
            key = unicode(item)

            try:
                return super(Object, self).__getitem__(unicode(item))
            except KeyError:
                if self.prototype:
                    try:
                        return self.prototype[key]
                    except KeyError:
                        pass

                return undefined

        def __setitem__(self, item, value):
            return super(Object, self).__setitem__(item, value)

        def prefixincr(self, item, increment):
            value = self[item] + increment
            self[item] = value
            return value

        def postfixincr(self, item, increment):
            value = self[item]
            self[item] = value + increment
            return value

        def __eq__(self, other):
            return False

        def __repr__(self):
            return "Object(%s)" % dict.__repr__(self)

        def __nonzero__(self):
            return True

    class Array(Object):
        def __init__(self, value, prototype=None):
            Object.__init__(self, prototype=prototype)

            self.items = list(value)

        @javascript
        def push(this, arguments):
            this.items.extend(arguments)

            return len(this.items)

        @javascript
        def concat(this, arguments):
            result = this.items[:]

            for arg in arguments:
                if isinstance(arg, Array):
                    result.extend(arg)
                else:
                    result.append(arg)

            return result

        def pop(self, *args):
            return self.items.pop(*args)

        def __len__(self):
            return len(self.items)

        def __getitem__(self, item):
            try:
                return self.items[int(item)]
            except (IndexError, ValueError):
                return Object.__getitem__(self, item)

        def __repr__(self):
            return repr(self.items)

    class Boolean(Object):
        def __init__(self, value=False, prototype=None):
            Object.__init__(self, prototype=prototype)

            self.value = bool(value)

        def __repr__(self):
            return repr(self.value)


    class Number(Object):
        NaN = object()

        def __init__(self, number=0, prototype=None):
            Object.__init__(self, prototype=prototype)

            self.number = number

        def __repr__(self):
            if self.number is self.NaN:
                return 'NaN'

            return repr(self.number)


    class Function(Object):
        def __init__(self, code, parameters=None, scope=None, prototype=None):
            Object.__init__(self, prototype=prototype)
            
            self.code = code
            self.parameters = parameters or []
            self.scope = scope or Scope()

        @javascript
        def apply(this, arguments):
            if not callable(this):
                raise TypeError('Function.prototype.apply called on incompatible %r' % this)

            context = this

            if arguments:
                context = arguments[0]

            if len(arguments) > 1:
                if not isinstance(arguments[1], Array):
                    raise TypeError('second argument to Function.prototype.apply must be an array')

                arguments = arguments[1]
            else:
                arguments = Array()

            return this(instance, arguments)

        @javascript
        def call(this, arguments):
            if not callable(this):
                raise TypeError('Function.prototype.call called on incompatible %r' % this)

            if arguments:
                instance = arguments.pop(0)
            else:
                instance = this

            return this(instance, arguments)

        def __call__(self, this, arguments):
            scope = Scope(self.scope)

            scope.var('arguments', arguments)

            arguments['callee'] = self

            for i, p in enumerate(self.parameters):
                scope.var(p, arguments[i])

            return self.code(this, scope)

        def __repr__(self):
            return "Function(%s)" % dict.__repr__(self)


    class PythonFunction(Function):
        def __init__(self, code, prototype):
            Object.__init__(self, prototype)

            self.code = code

        def __call__(self, this, arguments):
            return self.code(this, arguments)


    class String(Object):
        def __init__(self, s, prototype=None):
            Object.__init__(self, prototype=prototype)

            self.string = unicode(s)

        def __add__(self, other):
            if not isinstance(other, String):
                return String(self.string + String(other))

            return String(self.string + other)

        def __repr__(self):
            return repr(self.string)

    true = Boolean(True)
    false = Boolean(False)
    NaN = Number(Number.NaN)

    globals = locals()

    scope = Scope(globals)

    return locals()


if __name__ == '__main__':
    print init()
