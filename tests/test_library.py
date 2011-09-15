import codecs
import os.path

from pybemhtml.compiler import Compiler

basedir = os.path.dirname(__file__)

source = codecs.open(os.path.join(basedir, 'test_library.js'), encoding='utf-8').read()    

python = Compiler().compile(source)

codecs.open(os.path.join(basedir, 'test_library_js.py'), 'w', encoding='utf-8').write(python)

from test_library_js import scope, undefined, Array, PythonFunction

def _assert(this, arguments):
    assert(arguments[0])

scope['assert'] = PythonFunction(_assert)

scope['tests'](undefined, Array())
