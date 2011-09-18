# Javascript objects

import random
import re
import simplejson


class ReferenceError(Exception):
    pass


class InternalError(Exception):
    pass


class RangeError(Exception):
    pass


class Scope(object):
    def __init__(self, parent=None):
        self.variables = {}
        self.parent = parent
        super(Scope, self).__init__()

    def __getitem__(self, item):
#        if item == 'undefined':
#            return undefined

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

    def update(self, item, function, postfix, *args):
        value = self[item]
        newvalue = function(value)
        self[item] = newvalue

        if postfix:
            return value

        return newvalue


def getproperty(object, property):
    if isinstance(object, dict):
        return Object.getproperty(object, property)

    if isinstance(object, unicode):
        return Object.getproperty(String.prototype, property)

    if isinstance(object, list):
        return Array.getproperty(object, property)

    if isinstance(object, Object):
        return object[property]

    if hasattr(object, '__call__'):
        return PythonFunction.getproperty(object, property)

    raise InternalError('Unknown object type %r', object)


def setproperty(object, property, value):
    if isinstance(object, dict):
        object[property] = value
        return value

    if isinstance(object, list):
        Array.setproperty(object, property, value)
        return value

    if isinstance(object, Object):
        object[property] = value
        return value
    
    raise InternalError('Unknown object type %r', object)


def updateproperty(object, property, function, postfix, *args):
    value = getproperty(object, property)
    newvalue = function(value)
    setproperty(object, property, newvalue)

    if postfix:
        return value

    return newvalue


def incr(value):
    return value + 1


def decr(value):
    return value - 1


def deleteproperty(object, property):
    if isinstance(object, dict):
        del object[property]
        return True

    raise InternalError("Don't know how to delete properties of %r" % object)


def enumerate_properties(object):
    if isinstance(object, dict):
        return Object.enumerate(object)

    if isinstance(object, list):
        return Array.enumerate(object)

    if isinstance(object, basestring):
        return Object.enumerate(String.prototype)

    if isinstance(object, Object):
        return object.enumerate(object)

    raise InternalError("Don't know how to enumerate %r" % object)


def forinloop(this, scope, item, iterator, statement):
    for value in enumerate_properties(iterator):
        scope.var(item, value)
        
        statement(this, scope)

    return undefined


def new(objectType, parameters):
    if getattr(objectType, 'constructor'):
        return objectType(None, parameters)

    this = Object()
    this.prototype = objectType['prototype']

    objectType(this, parameters)
    return this


def typeof(value):
    if isinstance(value, int):
        return 'number'

    if isinstance(value, float):
        return 'number'

    if isinstance(value, basestring):
        return 'string'

    if isinstance(value, list):
        return 'object'

    if isinstance(value, Function) or hasattr(value, '__call__'):
        return 'function'

    if isinstance(value, dict):
        return 'object'

    if value is undefined:
        return 'undefined'

    if value is True or value is False:
        return 'boolean'

    raise InternalError("Unknown object %r" % value)


def whileloop(this, scope, condition, statement):
    while condition(scope):
        statement(this, scope)

    return undefined


class Base(object):
    pass


class UndefinedType(Base):
    def __getitem__(self, item):
        raise TypeError('undefined has no property %r' % item)
        raise TypeError('undefined has no properties')

    def __str__(self):
        return 'undefined'

    def __repr__(self):
        return 'undefined'

    def __call__(self, this, arguments):
        raise TypeError('call to undefined with arguments %r %r' % (this, arguments))
        raise TypeError('undefined is not a function')

    def __add__(self, other):
        if isinstance(other, int) or isinstance(other, float):
            return NaN
        
        if isinstance(other, basestring):
            return 'undefined' + other

    def __radd__(self, other):
        if isinstance(other, int) or isinstance(other, float):
            return NaN
        
        if isinstance(other, basestring):
            return other + 'undefined'

    def __sub__(self, other):
        if isinstance(other, int) or isinstance(other, float):
            return NaN

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
                name = getattr(value, 'name', key)
                properties[name] = dict.pop(key)

        dict['properties'] = properties
            
        klass = type.__new__(mcs, name, bases, dict)

        klass.__name__ = name

        return klass


def javascript(method):
    method.js = True
    return method


class Object(Base):
    __metaclass__ = javascript_object

    def __init__(self, properties={}):
        self.properties = {}

        self.update(properties)

    def update(self, properties):
        for property, value in properties.items():
            if hasattr(value, '__call__') and not isinstance(value, Function):
                value = PythonFunction(value)

            self.properties[property] = value
                
    def new(this, arguments):
        return dict()

    @classmethod
    def enumerate(cls, this):
        enumerable = this.keys()

        return sorted(enumerable)

    @javascript
    def hasOwnProperty(this, arguments): 
        prop = arguments[0]

        return prop in this

    @javascript
    def toString(this, arguments):
        if isinstance(this, dict):
            return '[object Object]';

        if isinstance(this, list):
            return '[object Array]'

        if isinstance(this, basestring):
            return '[object String]'

        return '[object %s]' % this.__class__.__name__

    def __getitem__(self, property):
        try:
            return self.properties[unicode(property)]
        except KeyError:
            if self.prototype:
                return self.prototype[property]

        return undefined

    def __setitem__(self, property, value):
        self.properties[property] = value
        return value

    @classmethod
    def getproperty(cls, this, property):
        try:
            return this[unicode(property)]
        except KeyError:
            pass

        if this is cls.prototype:
            return undefined

        return getproperty(cls.prototype, property)

    @classmethod
    def setproperty(cls, this, property, value):
        this[unicode(property)] = value
        return value

    
    def __repr__(self):
        return 'Object { %s }' % ", ".join("%s=%s" % item for item in self.properties.items())


class Number(Object):
    NaN = object()

    def __init__(self, number):
        Object.__init__(self)
        self.number = number
        
    def __repr__(self):
        if self.number is self.NaN:
            return 'NaN'

        return repr(self.number)

    def __add__(self, other):
        return NaN

    def __sub__(self, other):
        return NaN


class Array(Object):
    extraproperties = {}

    def __new__(cls, *args, **kwargs):
        raise InternalError("Array object should not be instantiated")

    @staticmethod
    def new(this, arguments):
        if len(arguments) == 1:
            length = arguments[0]

            if isinstance(length, float):
                if int(length) != length:
                    raise RangerError('invalid array length')
                
                length = int(length)

            if isinstance(length, int):
                if length < 0:
                    raise RangeError('invalid array length')

                return [undefined] * length

        return arguments

    @javascript
    def push(this, arguments):
        if isinstance(this, list):
            this.extend(arguments)
            return len(this)

        raise InternalError('Push is not implemented for %r' % this)
            
    @javascript
    def join(this, arguments):
        return arguments[0].join(unicode(arg) for arg in this)

    @javascript
    def unshift(this, arguments):
        this[0:0] = arguments
        return len(this)

    @classmethod
    def coerceindex(cls, property):
        if isinstance(property, int):
            if property < 0:
                return None

            index = property

        if isinstance(property, float):
            index = int(property)

            if index != property:
                return None

        if isinstance(property, basestring):
            try:
                index = int(property, 10)
            except ValueError:
                return None
            
        if index < 0:
            return None

        return index

    @classmethod
    def getproperty(cls, this, property):
        if property == 'length':
            return len(this)

        index = cls.coerceindex(property)

        if index is not None:
            try:
                return this[index]
            except IndexError:
                pass

        try:
            return cls.extraproperties[id(this)][unicode(property)]
        except KeyError:
            pass

        return getproperty(cls.prototype, property)

    @classmethod
    def setproperty(cls, this, property, value):
        if property == 'length':
            length = cls.coerceindex(value)
            if length is None:
                raise RangeError("invalid array length")
            if length < len(this):
                this[:] = this[:length]
            if length > len(this):
                this.extend([undefined] * (length - len(this)))

            return length

        index = cls.coerceindex(property)

        if index is not None:
            if len(this) <= index:
                this.extend([undefined] * (index - len(this) + 1))
                
            this[index] = value

        cls.extraproperties.setdefault(id(this), {})[unicode(property)] = value

        return value


class Boolean(Object):
    pass


class Function(Object):
    def __init__(self, code=None, parameters=[], scope=None, name='function'):
        Object.__init__(self)

        self.name = name
        self.code = code
        self.parameters = parameters
        self.scope = scope or Scope()

        self['length'] = Number(len(parameters))
        self['prototype'] = {}

    @javascript
    def apply(this, arguments):
        if not hasattr(this, '__call__'):
            raise TypeError('Function.prototype.apply called on incompatible %r' % this)

        context = this

        if arguments:
            context = arguments[0]

        if len(arguments) > 1:
            if not isinstance(arguments[1], list):
                raise TypeError('second argument to Function.prototype.apply must be an array')

            arguments = arguments[1]
        else:
            arguments = list()

        return this(context, arguments)

    @javascript
    def call(this, arguments):
        if not hasattr(this, '__call__'):
            raise TypeError('Function.prototype.call called on incompatible %r' % this)

        if arguments:
            instance = arguments.pop(0)
        else:
            instance = this

        return this(instance, arguments)

    def __call__(self, this, arguments):
        scope = Scope(self.scope)

        scope.var('arguments', arguments)

        setproperty(arguments, 'callee', self)

        for i, p in enumerate(self.parameters):
            try:
                scope.var(p, arguments[i])
            except IndexError:
                scope.var(p, undefined)

        return self.code(this, scope)

    def __repr__(self):
        return "%s()" % self.name


class PythonFunction(Function):
    def __init__(self, callable=None):
        Object.__init__(self)

        if callable:
            self['prototype'] = getattr(callable, 'prototype', {})
            self.name = callable.__name__
        else:
            self.name = 'function'

        self.constructor = hasattr(callable, 'new')

        self.callable = getattr(callable, 'new', callable)

    def __call__(self, this, arguments):
        return self.callable(this, arguments)

    @classmethod
    def getproperty(cls, this, property):
        return cls.prototype[property]

        raise InternalError()


class String(Object):
    @javascript
    def replace(this, arguments):
        pattern = arguments[0]
        replacement = arguments[1]

        if isinstance(replacement, Function):
            def replacement_function(match):
                arguments = [match.group()] + list(match.groups()) + [match.start(), this]
                return replacement(undefined, arguments)

        if isinstance(pattern, RegExp):
            return pattern.replace(this, replacement_function or replacement)

        raise InternalError('unsupported object for pattern %r' % pattern)
   
    @javascript
    def substring(this, arguments):
        return this[arguments[0]:arguments[1]]


class RegExp(Object):
    FLAGS = re.compile("[gi]*")
    
    def __init__(self, pattern, flags):
        Object.__init__(self)
        
        re_flags = 0

        if not self.FLAGS.match(flags):
            raise InternalError('unsupported flags %s' % flags)

        if 'i' in flags:
            re_flags |= re.I

        self.all = 'g' in flags

        self.re = re.compile(unicode(pattern), re_flags)

    @staticmethod
    def new(this, arguments):
        return RegExp(arguments[0], arguments[1])

    def replace(self, string, replacement):
        count = 0 if self.all else 1

        return self.re.sub(replacement, string, count)

    def __repr__(self):
        return "RegExp"


class Math(Object):
    @javascript
    def random(this, arguments):
        return random.random()


class JSON(Object):
    @javascript
    def stringify(this, arguments):
        return simplejson.dumps(arguments[0])


Object.prototype = Object.properties
Array.prototype = Array.properties
Boolean.prototype = Boolean.properties
Number.prototype = Number.properties
RegExp.prototype = RegExp.properties
String.prototype = String.properties
Function.prototype = Function()
Function.prototype.update(Function.properties)
Function.prototype.prototype = None

NaN = Number(Number.NaN)

def log(this, arguments):
    import logging
    logging.getLogger().debug(" ".join(repr(arg) for arg in arguments))

console = {'log': PythonFunction(log)}

scope = Scope({
    'Array': PythonFunction(Array),
    'Boolean': PythonFunction(Boolean),
    'Function': PythonFunction(Function),
    'Number': PythonFunction(Number),
    'Object': PythonFunction(Object),
    'String': PythonFunction(String),
    'RegExp': PythonFunction(RegExp),
    'Math': Math.properties,
    'JSON': JSON.properties,
    'console': console,
})
