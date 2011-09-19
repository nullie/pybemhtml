import codecs
import os.path
import sys

from pybemhtml.compiler import Compiler

def test_library():
    basedir = os.path.dirname(__file__)

    source = codecs.open(os.path.join(basedir, 'data', 'library.js'), encoding='utf-8').read()    

    python = Compiler().compile(source)

    codecs.open(os.path.join(basedir, 'tmp', 'library_js.py'), 'w', encoding='utf-8').write(python)

    sys.path.append(os.path.join(basedir, 'tmp'))

    from library_js import scope
    from pybemhtml.library import undefined, PythonFunction

    scope['tests'](undefined, [])
