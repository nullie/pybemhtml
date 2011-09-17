# Javascript objects

import re


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


def new(constructor, arguments):
    constructor['constructor']
    this = Object(prototype=constructor['constructor'])
    constructor(this, arguments)
    return this
    

def forinloop(this, scope, item, iterator, statement):
    for value in iterator.enumerate():
        scope.var(item, value)
        
        statement(this, scope)

    return undefined


def whileloop(this, scope, condition, statement):
    while condition(scope):
        statement(this, scope)

    return undefined


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
        
        if isinstance(other, String):
            return String('undefined' + other.string)

    def __eq__(self, other):
        return False

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


class Constructor(object):
    def __init__(self, klass, prototype):
        self.klass = klass

        if isinstance(prototype, Constructor):
            self.prototype = prototype(klass.properties)
        else:
            self.prototype = prototype
            self.prototype.properties.update(klass.properties)

    def __call__(self, *args, **kwargs):
        object = self.klass(*args, **kwargs)
        object.prototype = self.prototype
        return object


class Object(Base):
    __metaclass__ = javascript_object

    def __init__(self, properties={}):
        self.prototype = None
        self.properties = properties.copy()

    @javascript
    def hasOwnProperty(this, arguments): 
        prop = arguments[0]

        return prop in this.properties

    @javascript
    def toString(this, arguments):
        return String('[object %s]' % this.__class__.__name__)

    def __getitem__(self, item):
        try:
            return self.properties[unicode(item)]
        except KeyError:
            pass

        if self.prototype:
            try:
                return self.prototype[item]
            except KeyError:
                pass

        return undefined

    def __setitem__(self, item, value):
        self.properties[unicode(item)] = value
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


class Immutable(Object):
    def __setitem__(self, item, value):
        return value


class Number(Immutable):
    NaN = object()

    def __init__(self, number=0):
        self.number = number
        
    def __hash__(self):
        return self.number

    def __add__(self, other):
        return Number(self.number + other)

    def __sub__(self, other):
        return Number(self.number - other.number)

    def __eq__(self, other):
        if isinstance(other, Number):
            return self.number == other.number

        return self.number == other.number
    
    def __cmp__(self, other):
        if isinstance(other, Number):
            return cmp(self.number, other.number)

        return cmp(self.number, other)

    def __neg__(self):
        return Number(-self.number)

    def __repr__(self):
        if self.number is self.NaN:
            return 'NaN'

        return repr(self.number)


class Array(Object):
    def __init__(self, value=[]):
        self.items = value        
        self['length'] = Number(len(value))

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
    def new(this, arguments):
        if len(arguments) == 1 and isinstance(arguments[0], Number):
            return Array([undefined] * arguments[0].number)

        return arguments

    def __iter__(self):
        return iter(self.items)

    def enumerate(self):
        for property in self.properties:
            yield String(property)

    def pop(self, *args):
        return self.items.pop(*args)

    def __len__(self):
        return len(self.items)
    
    def parseindex(self, item):
        index = None

        if isinstance(item, int):
            index = item
        elif isinstance(item, Number):
            index = int(item.number)
        elif isinstance(item, String):
            try:
                index = int(item.string, 10)
            except ValueError:
                return None

        if str(index) != str(item):
            return None
        
        if index < 0:
            return None

        return index

    def __getitem__(self, item):
        index = self.parseindex(item)

        if index is not None:
            try:
                return self.items[index]
            except IndexError:
                pass

        return Object.__getitem__(self, item)

    def __setitem__(self, item, value):
        index = self.parseindex(item)

        if index is not None:
            if self['length'] <= index:
                self.items.extend([undefined] * (index - self['length'].number + 1))
                self['length'] = index + 1
                
            self.items[index] = value

        return Object.__setitem__(self, item, value)

    def __repr__(self):
        return repr(self.items)


class Boolean(Object):
    def __init__(self, value=False):
        self.value = bool(value)

    def __repr__(self):
        return repr(self.value)


class Function(Object):
    def __init__(self, code=None, parameters=[], scope=None, name='function'):
        self.name = name
        self.code = code
        self.parameters = parameters
        self.scope = scope or Scope()

        self['length'] = Number(len(parameters))
        self['prototype'] = Object()

    @javascript
    def apply(this, arguments):
        if not hasattr(this, '_call'):
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
        self.callable = getattr(callable, 'new', callable)

        if prototype:
            self.prototype = prototype

        if callable:
            self['prototype'] = getattr(callable, 'prototype', Object())
    
    def __call__(self, this, arguments):
        return self.callable(this, arguments)

    def __repr__(self):
        if self.callable:
            return "%s()" % self.callable.__name__ 

        return "function()"


class String(Immutable):
    def __init__(self, s):
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

    def __unicode__(self):
        return self.string

    def __repr__(self):
        return '"%s"' % self.string


class RegExp(Object):
    def __init__(self, pattern, flags):
        self.re = re.compile(unicode(pattern))

    @staticmethod
    def new(this, arguments):
        return RegExp(arguments[0], arguments[1])

_Object = Constructor(Object, Object(Object.properties))
_Array = Constructor(Array, _Object)
_Boolean = Constructor(Boolean, _Object)
_Number = Constructor(Number, _Object)
_RegExp = Constructor(RegExp, _Object)
_String = Constructor(String, _Object)
_Function = Constructor(Function, Function(_Object()))

true = _Boolean(True)
false = _Boolean(False)
NaN = _Number(Number.NaN)

def log(this, arguments):
    print arguments

console = _Object({'log': _Function(log)})

scope = Scope({
    'Array': _Function(Array.new),
    'Boolean': _Function(_Boolean),
    'Function': _Function(_Function),
    'Number': _Function(_Number),
    'Object': _Function(_Object),
    'String': _Function(_String),
    'RegExp': _Function(_RegExp),
    'console': console,
})
