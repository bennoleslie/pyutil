"""namedfields provides an alternative approach to creating named tuples.

See http://benno.id.au/blog/2014/11/30/a-better-namedtuple for an introduction
to some of the motivations.
"""

from operator import itemgetter


def __namedfield_repr(self):
    'Return a nicely formatted representation string'
    fmt = '(' + ', '.join('%s=%%r' % x for x in self._fields) + ')'
    return self.__class__.__name__ + fmt % self


def __namedfield_asdict(self):
    'Return a new OrderedDict which maps field names to their values'
    return OrderedDict(zip(self._fields, self))


# Pickling helpers
def __namedfield_getnewargs(self):
    'Return self as a plain tuple.  Used by copy and pickle.'
    return tuple(self)


def __namedfield_getstate(self):
    'Exclude the OrderedDict from pickling'
    return None


@classmethod
def __namedfield_make(cls, iterable):
    'Make a new tuple object from a sequence or iterable'
    result = tuple.__new__(cls, iterable)
    if len(result) != len(cls._fields):
        raise TypeError('Expected {} arguments, got {}'.format(len(self._fields), len(result)))
    return result


def __namedfield_replace(_self, **kwds):
    'Return a new tuple object replacing specified fields with new values'
    result = _self._make(map(kwds.pop, _self._fields, _self))
    if kwds:
        raise ValueError('Got unexpected field names: %r' % list(kwds))
    return result


def namedfields(*fields):
    def inner(cls):
        if not issubclass(cls, tuple):
            raise TypeError("namefields decorated classes must be subclass of tuple")

        str_fields = ", ".join(fields)
        new_method = eval("lambda cls, {}: tuple.__new__(cls, ({}))".format(str_fields, str_fields), {}, {})

        attrs = {
            '__slots__': (),
            '_fields': fields,
            '__new__': new_method,
            '__repr__': __namedfield_repr,
            '__dict__': property(__namedfield_asdict),
            '_asdict': __namedfield_asdict,
            '__getnewargs__': __namedfield_getnewargs,
            '__getstate__': __namedfield_getstate,
            '_make': __namedfield_make,
            '_replace': __namedfield_replace,
        }

        attrs.update({fld: property(itemgetter(idx), doc='Alias for field number {}'.format(idx))
                      for idx, fld in enumerate(fields)})

        attrs.update({key: val for key, val in cls.__dict__.items()
                      if key not in ('__weakref__', '__dict__')})

        return type(cls.__name__, cls.__bases__, attrs)

    return inner


def extendedfields(*fields):
    def inner(cls):
        if not issubclass(cls, tuple):
            raise TypeError("extendednamedfield decorated classes must be subclass of tuple")

        try:
            base_fields = cls.__bases__[0]._fields
        except AttributeError:
            raise TypeError("extendednamedfield decorated classes must subclass a class decorate by namedfields")

        str_fields = ", ".join(base_fields + fields)
        new_method = eval("lambda cls, {}: tuple.__new__(cls, ({}))".format(str_fields, str_fields))

        attrs = {
            '__slots__': (),
            '_fields': base_fields + fields,
            '__new__': new_method
        }

        attrs.update({fld: property(itemgetter(idx), doc='Alias for field number {}'.format(idx))
                      for idx, fld in enumerate(fields, len(base_fields))})

        attrs.update({key: val for key, val in cls.__dict__.items()
                      if key not in ('__weakref__', '__dict__')})

        return type(cls.__name__, cls.__bases__, attrs)

    return inner
