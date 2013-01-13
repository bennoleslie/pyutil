"""Snipppets of potentially reusable code that don't deserve their
own library."""

import bisect

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


def test_dict_inverse():
    assert dict_inverse({1: 'a', 2: 'a', 3: 'c'}) == {'a': [1, 2], 'c': [3]}
    assert dict_inverse({1: 'a', 2: 'b', 3: 'c'}, True) == {'a': 1, 'b': 2, 'c': 3}
