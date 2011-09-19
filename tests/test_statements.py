import sys
from os import path

from pybemhtml.compiler import Compiler


def test_break():
    source = u"""
    i = 0
    label1: {
        label2: {
            label3: {
                break label2;
                i = 1;
            }
        }
        i = 2;
    }

    console.log(i);

    assert(i == 2);
    """

    python = Compiler().compile(source)

    basedir = path.dirname(__file__)

    open(path.join(basedir, 'tmp', 'statements_js.py'), 'w').write(python)

    sys.path.append(path.join(basedir, 'tmp'))

    import statements_js


def test_switch():
    source = u"""
    i = 0
    switch("test") {
        case "foo":
            console.log('not ok');
            i = 1;
            break;
        case "test":
            console.log('ok');
            i = 2;
            break;
    }

    assert(i == 2);
    """

    python = Compiler().compile(source)

    basedir = path.dirname(__file__)

    open(path.join(basedir, 'tmp', 'statements_switch.py'), 'w').write(python)

    sys.path.append(path.join(basedir, 'tmp'))

    import statements_switch
