"""Snipppets of potentially reusable code that don't deserve their
own library."""

import bisect
import contextlib
import inspect
import os
import shutil
import signal
import sys
import tempfile
import unittest
from functools import wraps


class Location:
    def __init__(self, name, line, col):
        self.name = name
        self.line = line
        self.col = col

    def __str__(self):
        return "{}:{}.{}".format(self.name, self.line, self.col)


class Locator:
    """Locator provides a way to convert an absolute offset in a
    string into a Location object.

    """

    def __init__(self, data, name='<string>'):
        self.name = name
        self.line_offsets = [0]
        for line_len in map(len, data.splitlines(True)):
            self.line_offsets.append(self.line_offsets[-1] + line_len)

    def locate(self, offset):
        """Return a Location() object for the given offset."""
        line = bisect.bisect_right(self.line_offsets, offset)
        col = offset - self.line_offsets[line - 1]
        return Location(self.name, line, col)


def import_from_dir(module_name, dir_name):
    """Import a module form a specific directory.

    Sometimes you might want to load a package from a specific
    directory. For example, you may be loading a plugin of some
    description.

    This function ensures that only modules from a specific
    directory are loaded to avoid any chance of loading a
    module of the same name from somewhere else.

    After loading the module is removed from sys.modules to
    avoid other namespace clashes.

    """
    saved_sys_path = sys.path
    saved_module = None
    if module_name in sys.modules:
        saved_module = sys.modules[module_name]
    try:
        module = __import__(module_name)
        return module
    finally:
        sys.path = saved_sys_path
        if saved_module:
            sys.modules[module_name] = saved_module
        else:
            del sys.modules[module_name]


def dict_inverse(dct, exact=False):
    """Given an input dictionary (`dct`), create a new dictionary
    where the keys are indexed by the values. In the original
    dictionary multiple keys may reference the same value, so the
    values in the new dictionary is a list of keys. The order of keys
    in the list is undefined.

    Example:

    > dict_inverse({1: 'a', 2: 'a', 3: 'c'})
    { 'a': [1, 2], 'c': [3]

    If `dct` has an exact inverse mapping `exact` can be passed as
    True. In this case, the values will be just the original key (not
    a list).

    Example:

    > dict_inverse({1: 'a', 2: 'b', 3: 'c'}, exact=True)
    { 'a': 1, 'b': 2, 'c': 3}

    Note: No checking is done when exact is True, so in the case
    where there are multiple keys mapping the same value it is
    undefined as to which key the value will map to.

    """
    if exact:
        return {value: key for key, value in dct.items()}

    r = {}
    for key, value in dct.items():
        r.setdefault(value, []).append(key)
    return r


class _GeneratorSimpleContextManager(contextlib._GeneratorContextManager):
    """Helper for @simplecontextmanager decorator."""

    def __exit__(self, type, value, traceback):
        if type is None:
            try:
                next(self.gen)
            except StopIteration:
                return
            else:
                raise RuntimeError("generator didn't stop")
        else:
            if value is None:
                # Need to force instantiation so we can reliably
                # tell if we get the same exception back
                value = type()

            try:
                next(self.gen)
            except StopIteration as exc:
                # Suppress the exception *unless* it's the same exception that
                # was passed to throw().  This prevents a StopIteration
                # raised inside the "with" statement from being suppressed
                return exc is not value
            else:
                raise RuntimeError("generator didn't stop")
            finally:
                return False


def simplecontextmanager(func):
    """@simplecontextmanager decorator.

    Typical usage:

        @simplecontextmanager
        def some_generator(<arguments>):
            <setup>
            yield <value>
            <cleanup>

    This makes this:

        with some_generator(<arguments>) as <variable>:
            <body>

    equivalent to this:

        <setup>
        try:
            <variable> = <value>
            <body>
        finally:
            <cleanup>

    """
    @wraps(func)
    def helper(*args, **kwds):
        return _GeneratorSimpleContextManager(func, *args, **kwds)
    return helper


@simplecontextmanager
def chdir(path):
    """Current-working directory context manager.

    Makes the current working directory the specified `path` for the
    duration of the context.

    Example:

    with chdir("newdir"):
        # Do stuff in the new directory
        pass

    """
    cwd = os.getcwd()
    os.chdir(path)
    yield
    os.chdir(cwd)


@simplecontextmanager
def umask(new_mask):
    """unmask context manager.

    Makes `new_mask` the current mask, and restores the previous umask
    after the context closes.

    """
    cur_mask = os.umask(new_mask)
    yield
    os.umask(cur_mask)


@simplecontextmanager
def update_env(env):
    """os.environ context manager.

    Updates os.environ with the specified `env` for the duration of the context.

    """
    old_env = {}
    for key in env:
        old_env[key] = os.environ.get(key)
        os.environ[key] = env[key]

    yield

    for key in old_env:
        if old_env[key] is None:
            del os.environ[key]
        else:
            os.environ[key] = old_env[key]


@simplecontextmanager
def tempdir():
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir)


def touch(path):
    """Create an empty file (just like the unix touch command)."""
    open(path, 'w').close()


def file_list(root, full_path=False, sort=True):
    if not root.endswith('/'):
        root += '/'
    for base, dirs, files in os.walk(root):
        if sort:
            dirs.sort()
            files.sort()
        if not full_path:
            base = base[len(root):]
        for f in files:
            yield os.path.join(base, f)


SIG_NAMES = dict((k, v) for v, k in signal.__dict__.items() if v.startswith('SIG'))


def show_exit(exit_code):
    sig_num = exit_code & 0xff
    exit_status = exit_code >> 8
    if sig_num == 0:
        return "exit: {}".format(exit_status)
    else:
        return "signal: {}".format(SIG_NAMES.get(sig_num, 'Unknown signal {}'.format(sig_num)))


class TestUtil(unittest.TestCase):

    def test_chdir(self):
        cur = os.getcwd()
        with chdir('/'):
            assert os.getcwd() == '/'
        assert os.getcwd() == cur

    def test_dict_inverse(self):
        assert dict_inverse({1: 'a', 2: 'a', 3: 'c'}) == {'a': [1, 2], 'c': [3]}
        assert dict_inverse({1: 'a', 2: 'b', 3: 'c'}, True) == {'a': 1, 'b': 2, 'c': 3}

    def test_simplecontextmanager(self):
        before = None
        after = None

        @simplecontextmanager
        def foo():
            nonlocal before
            nonlocal after
            after = None
            before = True
            yield 1
            after = True

        with foo() as x:
            assert x == 1
            assert before
            assert after is None
        assert before
        assert after

        try:
            with foo() as x:
                assert x == 1
                assert before
                assert after is None
                raise Exception('check')
        except Exception as exc:
            assert exc.args == ('check', )
            assert before
            assert after
        else:
            assert False

    def test_simplecontextmanager_double_yield(self):
        before = None
        after = None

        @simplecontextmanager
        def foo():
            nonlocal before
            nonlocal after
            after = None
            before = True
            yield 1
            yield 2
            after = True

        try:
            with foo() as x:
                assert x == 1
                assert before
                assert after is None
        except RuntimeError as exc:
            assert exc.args == ("generator didn't stop", )
        else:
            assert False

    def test_simplecontextmanager_raise(self):
        before = None
        after = None

        @simplecontextmanager
        def foo():
            nonlocal before
            nonlocal after
            after = None
            before = True
            yield 1
            raise Exception("with")

        try:
            with foo() as x:
                assert x == 1
                assert before
                assert after is None
        except Exception as exc:
            assert exc.args == ('with', )
            assert before
            assert after is None
        else:
            assert False

        try:
            with foo() as x:
                assert x == 1
                assert before
                assert after is None
                raise Exception("check")
        except Exception as exc:
            assert exc.args == ('check', )
            assert before
            assert after is None
        else:
            assert False

    def test_tempdir(self):
        tempdir_name = None
        with tempdir() as t:
            tempdir_name = t
            assert os.path.exists(tempdir_name)

        assert not os.path.exists(tempdir_name)

        try:
            with tempdir() as t:
                tempdir_name = t
                assert os.path.exists(tempdir_name)
                raise Exception('tempdir_with_fail')
        except Exception as exc:
            assert exc.args == ('tempdir_with_fail', )
        else:
            assert False

        assert not os.path.exists(tempdir_name)

    def test_file_list(self):
        with tempdir() as t:
            touch(os.path.join(t, 'b'))
            touch(os.path.join(t, 'a'))
            os.mkdir(os.path.join(t, 'c'))
            touch(os.path.join(t, 'c', '1'))
            assert list(file_list(t)) == ['a', 'b', 'c/1']

    def test_show_exit(self):
        assert show_exit(os.system("exit 1")) == "exit: 1"
        assert show_exit(os.system("exit 2")) == "exit: 2"
        assert show_exit(os.system("kill -9 $$")) == "signal: SIGKILL"


def get_gcc_headers():
    """Get the header locations."""
    output = subprocess.check_output(["arm-none-eabi-cpp", "-Wp,-v"], stderr=subprocess.STDOUT, stdin=subprocess.PIPE).decode().splitlines()
    start = False
    include_paths = []
    for line in output:
        if not start and line == '#include <...> search starts here:':
            start = True
        elif start:
            if line == 'End of search list.':
                break
            else:
                include_paths.append(line.strip())
    return include_paths


def range1(n):
    yield from range(1, n + 1)


def debug(msg):
    print(msg.format(**inspect.stack()[1][0].f_locals))


class SysExit(Exception):
    def __init__(self, code, msg=None):
        super().__init__()
        self.code = code
        self.msg = msg


def script():
    s = inspect.stack()[1][0]
    caller_name = s.f_locals['__name__']
    if caller_name != '__main__':
        return

    caller_main = s.f_locals.get('main')
    if caller_main is None:
        print("main() not found.", file=sys.stderr)
        sys.exit(1)
    try:
        sys.exit(caller_main())
    except SysExit as e:
        if e.msg:
            print(e.msg, file=sys.stderr)
        sys.exit(e.code)
    except KeyboardInterrupt:
        # FIXME: This could probably be handled
        # better to match the Ctrl-C signal exit
        # code
        sys.exit(1)


def camelify(name):
    """Change from foo_bar => FooBar"""
    return ''.join([i.capitalize() for i in name.split('_')])


def yield_until_exception(exception, fn):
    """Generate values be repeatedly calling fn() until the specified exception
    is raised.

    """
    while True:
        try:
            yield fn()
        except exception:
            break


def attr_dict(itr, attr):
    """Given an iterable create a dictionary of the values indexed by a named attribute."""
    return {getattr(x, attr): x for x in itr}


def attr_dict_grouped(itr, attr):
    d = {}
    for v in itr:
        d.setdefault(getattr(v, attr), []).append(v)
    return d


def attr_dict_frozen(itr, attr):
    """Given an iterable create a dictionary of the values indexed by a named attribute."""
    return frozendict(attr_dict(itr, attr))


class frozendict(dict):
    """Inspired from: http://code.activestate.com/recipes/414283-frozen-dictionaries/"""
    __slots__ = ('_hash')

    @property
    def _blocked_attribute(obj):
        raise AttributeError("A frozendict cannot be modified.")

    __delitem__ = __setitem__ = clear = _blocked_attribute
    pop = popitem = setdefault = update = _blocked_attribute

    def __new__(cls, *args):
        new = dict.__new__(cls)
        dict.__init__(new, *args)
        new._hash = hash(frozenset(new.items()))
        return new

    def __init__(self, *args):
        pass

    def __hash__(self):
        return self._hash

    def __repr__(self):
        return "frozendict(%s)" % dict.__repr__(self)


def split_inclusive(lst, condition):
    start = 0
    for idx in range(len(lst)):
        if condition(lst[idx]):
            yield lst[start:idx]
            start = idx
    yield lst[start:]
