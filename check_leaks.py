"""Provides function for assisting the analysis of memory leaks in
Python modules.

For example, if you have a function `foo()` that you suspect may be
leaking memory do:

    check_leaks.monitor()
    foo()
    check_leaks.show()

This will show any objects that were allocated in `foo()` and could not
be garbage collected.

Note: Many standard Python modules perform memoization and/or delayed
initialization which can result in a lot of objects being shown as
memory leaks.

"""
import sys
import tracemalloc
import gc
import types

MAX_FRAMES = 25

before_objects = None


def _get_detail(obj):
    """Show a short representation of the given object.

    repr() itself is not used as it can result in very long
    strings that make viewing the report difficult.

    If no suitable representation can be found an empty string is
    returned.

    """
    detail = ''
    if repr(obj) < 200:
        return repr(obj)
    elif type(obj) in (list, tuple, dict):
        'len={}'.format(len(obj))
    else:
        return ''


def monitor():
    global before_objects
    gc.collect()
    before_objects = gc.get_objects()
    tracemalloc.start(MAX_FRAMES)


def show(filename=None):
    global before_objects
    gc.collect()
    after_objects = gc.get_objects()
    frame = sys._getframe()
    globals_ = globals()
    num_leaks = 0
    before_id_set = set(map(id, before_objects))
    if filename is not None:
        f = open(filename, 'w')
    else:
        f = sys.stderr

    for obj in after_objects:
        if id(obj) not in before_id_set:
            if obj in (before_objects, frame):
                continue
            num_leaks += 1
            print("Leak: id=0x{:x} type={} {}".format(id(obj), type(obj), _get_detail(obj)), file=f)
            tb = tracemalloc.get_object_traceback(obj)
            if tb is None:
                print("Traceback: None", file=f)
            else:
                print("Traceback:", file=f)
                print("\n".join(tb.format(MAX_FRAMES)), file=f)
            print(file=f)
            print("Referrers:", file=f)
            for ref in gc.get_referrers(obj):
                if ref in (after_objects, before_objects, frame, globals_):
                    continue
                print("     id=0x{:x} type={} {}".format(id(ref), type(ref), _get_detail(ref)), file=f)
                print("     traceback: {}".format(tracemalloc.get_object_traceback(ref)), file=f)
            print(file=f)
            print(file=f)
    print("Total leaks: {}".format(num_leaks), file=f)
    if filename is not None:
        f.close()
    tracemalloc.stop()
    gc.enable()
