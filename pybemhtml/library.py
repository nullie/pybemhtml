# Javascript objects

class ReferenceError(Exception):
    pass


class InternalError(Exception):
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
                try:
                    return self.parent[item]
                except KeyError:
                    pass

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
    if isinstance(value, Number):
        return String('number')

    if isinstance(value, String):
        return String('string')

    if isinstance(value, Function):
        return String('function')

    if isinstance(value, Object):
        return String('object')

    if value is undefined:
        return String('undefined')

    raise InternalError("Unknown object %r" % value)


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


class Base(object):
    pass


class UndefinedType(Base):
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
            return Number(Number.NaN)

    def __nonzero__(self):
        return False

    __setitem__ = __getitem__

undefined = UndefinedType()

del UndefinedType


class javascript_object(type):
    def __new__(mcs, name, bases, dict):
        properties = {}

        for key, value in dict.items():
            if isinstance(value, Base) or hasattr(value, 'js'):
                properties[key] = dict.pop(key)

        dict['properties'] = properties

        klass = type.__new__(mcs, name, bases, dict)

        klass.__name__ = name

        return klass


def javascript(method):
    method.js = True
    return method


class Object(Base):
    __metaclass__ = javascript_object

    def __init__(self, properties={}, parent=False):
        self.properties = dict(properties)

        if parent:
            self.prototype = None

    @javascript
    def hasOwnProperty(this, arguments): 
        prop = arguments[0]

        return prop in this.properties

    @javascript
    def toString(this, arguments):
        return String('[object %s]' % this.__class__.__name__)

    def __getitem__(self, item):
        try:
            return self.properties[item]
        except KeyError:
            pass

        if self.prototype:
            try:
                return self.prototype[item]
            except KeyError:
                pass

        return undefined

    def __setitem__(self, item, value):
        self.properties[item] = value
        return value

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
        return repr(self.properties)

    def __nonzero__(self):
        return True


Object.prototype = Object(Object.properties, parent=True)


class Immutable(Object):
    def __setitem__(self, item, value):
        return value


class Number(Immutable):
    NaN = object()

    def __init__(self, number=0):
        Object.__init__(self)

        self.number = number

    def __hash__(self):
        return self.number

    def __add__(self, other):
        return Number(self.number + other)

    def __eq__(self, other):
        return self.number == other.number

    def __repr__(self):
        if self.number is self.NaN:
            return 'NaN'

        return repr(self.number)


Number.prototype = Object(Number.properties)


class Array(Object):
    def __init__(self, value=[]):
        Object.__init__(self)

        self.items = list(value)

        self['length'] = Number(len(self.items))        

    length = Number(0)

    @javascript
    def push(this, arguments):
        length = this['length']

        for i, item in enumerate(arguments):
            this[length + i] = item

        length = length + len(arguments)

        this['length'] = length

        return length

    @javascript
    def concat(this, arguments):
        result = this.items[:]

        for arg in arguments:
            if isinstance(arg, Array):
                result.extend(arg)
            else:
                result.append(arg)

        return result

    @staticmethod
    def constructor(this, arguments):
        if len(arguments) == 1 and isinstance(arguments[0], int):
            return Array([undefined] * arguments[0])

        return Array(arguments)        

    def __iter__(self):
        return self.items.__iter__()

    def pop(self, *args):
        return self.items.pop(*args)

    def __len__(self):
        return len(self.items)

    def __getitem__(self, item):
        try:
            return self.items[int(item)]
        except (IndexError, ValueError):
            return Object.__getitem__(self, item)

    def __setitem__(self, item, value):
        if isinstance(item, Number):
            self.items[item.number] = value
            return value

        return Object.__setitem__(self, item, value)

    def __repr__(self):
        return repr(self.items)


Array.prototype = Object(Array.properties)


class Boolean(Object):
    def __init__(self, value=False):
        Object.__init__(self)

        self.value = bool(value)

    def __repr__(self):
        return repr(self.value)


Boolean.prototype = Object(Boolean.properties)


class Function(Object):
    def __init__(self, code=None, parameters=[], scope=None, name='function'):
        Object.__init__(self)

        self.name = name
        self.code = code
        self.parameters = parameters
        self.scope = scope or Scope()

        self['length'] = Number(len(parameters))

        self['prototype'] = Object()

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

        return this(context, arguments)

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
        return "%s()" % self.name


class PythonFunction(Function):
    def __init__(self, callable=None, prototype=None):
        Object.__init__(self)
        
        self.callable = getattr(callable, 'new', callable)

        if prototype:
            self.prototype = prototype

        if callable:
            self['prototype'] = getattr(callable, 'prototype', Object())
    
    def __call__(self, this, arguments):
        return self.callable(this, arguments)

    def __repr__(self):
        if self.constructor:
            return "%s()" % self.constructor.__name__ 

        return "function()"


PythonFunction.prototype = Function.prototype = PythonFunction(prototype=Object(Function.properties))


class String(Immutable):
    def __init__(self, s):
        Object.__init__(self)

        self.string = unicode(s)

    def __hash__(self):
        return hash(self.string)

    def __eq__(self, other):
        if isinstance(other, String):
            return Boolean(self.string == other.string)

        return false

    def __add__(self, other):
        if not isinstance(other, String):
            return String(self.string + String(other).string)

        return String(self.string + other.string)

    def __repr__(self):
        return repr(self.string)


String.prototype = Object(String.properties)


true = Boolean(True)
false = Boolean(False)
NaN = Number(Number.NaN)


def console_log(this, arguments):
    print repr(arguments)
    return undefined


scope = Scope({
    'Array': PythonFunction(Array),
    'Boolean': PythonFunction(Boolean),
    'Function': PythonFunction(PythonFunction),
    'Number': PythonFunction(Number),
    'Object': PythonFunction(Object),
    'String': PythonFunction(String),
    'console': Object({
         'log': PythonFunction(console_log),
    })
})
