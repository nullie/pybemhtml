# Javascript objects

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
    def __init__(self, *args):
        self.items = list(*args)

        self['concat'] = Function(self.concat)
        self['push'] = Function(self.push)

    @classmethod
    def push(cls, this, scope):
        this.items.extend(scope['arguments'])

    @classmethod
    def concat(cls, this, values):
        result = this.items[:]

        for value in values:
            if isinstance(value, Array):
                result.extend(value)
            else:
                result.append(value)

        return result

    def pop(self, *args):
        return self.items.pop(*args)

    def __len__(self):
        return len(self.items)

    def __getitem__(self, item):
        try:
            return self.items[int(item)]
        except (IndexError, ValueError):
            return super(Array, self).__getitem__(item)

    def __repr__(self):
        return repr(self.items)


class PythonFunction(Object):
    def __init__(self, code):
        self.code = code

    def __call__(self, this, arguments):
        return self.code(this, arguments)

    def __repr__(self):
        return "Function(%s)" % dict.__repr__(self)


class Function(Object):
    def __init__(self, code, parameters=None, scope=None):
        self.code = code
        self.parameters = parameters or []
        self.scope = scope or Scope()

    def __call__(self, this, arguments):
        scope = Scope(self.scope)

        scope.var('arguments', arguments)

        arguments['callee'] = self

        for i, p in enumerate(self.parameters):
            scope.var(p, arguments[i])

        return self.code(this, scope)

    def __repr__(self):
        return "Function(%s)" % dict.__repr__(self)


class NaNType(object):
    pass

NaN = NaNType()

del NaNType


class String(unicode):
    def __add__(self, other):
        if not isinstance(other, String):
            return self + String(other)

        return unicode.__add__(self, other)

    def __getitem__(self, item):
        try:
            return unicode[item]
        except (TypeError, IndexError):
            return undefined


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


def call(this, arguments):
    if not callable(this):
        raise TypeError('Function.prototype.call called on incompatible %r' % this)

    if arguments:
        instance = arguments.pop(0)
    else:
        instance = this

    return this(instance, arguments)


def tostring(this, arguments):
    if isinstance(this, int) or isinstance(this, float) or this is NaN:
        return '[object Number]'

    return '[object %s]' % this.__class__.__name__


def hasownproperty(this, arguments):
    prop = arguments[0]

    return prop in this


def typeof(value):
    if isinstance(value, Object):
        return 'object'

    if isinstance(value, str):
        return 'string'

    if isinstance(value, int):
        return 'number'

    if isinstance(value, float):
        return 'number'

    if value is undefined:
        return 'undefined'

    assert False


def forinloop(scope, item, iterator, statement):
    scope = Scope(scope)

    for value in iterator:
        scope.var(item, value)
        
        statement(scope)


def new(function, arguments):
    this = Object()
    this.update(function['prototype'] or {})
    function(this, arguments)
    return this
    


def whileloop(scope, condition, statement):
    scope = Scope(scope)

    while condition(scope):
        statement(scope)


def function(this, arguments):
    pass


def regexp(this, arguments):
    pass


def defaultscope():
    scope = Scope()

    scope['Function'] = PythonFunction(function)

    scope['Function']['prototype'] = Object({
        'apply': PythonFunction(apply),
        'call': PythonFunction(call),
        })

    scope['Object'] = Function()

    scope['Object']['prototype'] = Object({
        'hasOwnProperty': PythonFunction(hasownproperty),
        'toString': PythonFunction(tostring),
    })

    scope['RegExp'] = PythonFunction(regexp)
