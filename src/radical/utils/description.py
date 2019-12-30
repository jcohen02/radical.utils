
# ------------------------------------------------------------------------------
#
# We provide a base class for all kinds of description objects in theh RCT
# stack: job descriptions, task descriptions, pilot descriptions, workload
# descriptions etc.  That base class provides
#
#   - dict like API
#   - schema based type definitions
#   - optional runtime type checking
#
# The Description base class can, if so configured, provide an property API
# similar to the `ru.Config` class.
#
# NOTE: keys must not start with an underscore
#

import munch

from .misc import as_list


# ------------------------------------------------------------------------------
#
class Munch(munch.Munch):

    # --------------------------------------------------------------------------
    #
    def __init__(self, from_dict=None):
        '''
        create a munchified dictionary (tree) from `from_dict`.

        from_dict: data to be used for initialization

        NOTE: Keys containing an underscore are not exposed via the API.
              Keys containing dots are split and interpreted as paths in te
              configuration hierarchy.
        '''

        # TODO: `as_dict`, `keys` and `items` are reserved attributes.
        #       Should this list be smaller?

        if from_dict:
            self.update(from_dict)


    # --------------------------------------------------------------------------
    #
    # cfg['foo']        == cfg.foo
    # cfg['foo']['bar'] == cfg.foo.bar
    #
    def __getattr__(self, k):
        return self.get(k, None)

    def __setattr__(self, k, v):
        self[k] = v


    # --------------------------------------------------------------------------
    #
    # don't list private class attributes (starting with `_`) as dict entries
    #
    def __iter__(self):
        for k in dict.__iter__(self):
            if str(k).startswith('_'):
                continue
            yield k

    def items(self):
        for k in dict.__iter__(self):
            if str(k).startswith('_'):
                continue
            yield k, self[k]

    def keys(self):
        return [x for x in self]

    def __len__(self):
        return len(self.keys())


  # # --------------------------------------------------------------------------
  # #
  # def __str__(self):
  #     return str(self.as_dict())
  #
  #
  # # --------------------------------------------------------------------------
  # #
  # def __repr__(self):
  #     return str(self)
  #
  #
    # --------------------------------------------------------------------------
    #
    def as_dict(self):

        return self.toDict()  # from munch.Munch


    # --------------------------------------------------------------------------
    #
    @staticmethod
    def _verify_int(k, v, t):
        try   : return int(v)
        except: raise TypeError('expected int type for %s (%s)' % (k, type(v)))

    @staticmethod
    def _verify_str(k, v, t):
        try   : return str(v)
        except: raise TypeError('expected str type for %s (%s)' % (k, type(v)))

    @staticmethod
    def _verify_float(k, v, t):
        try   : return float(v)
        except: raise TypeError('expected float type for %s (%s)' % (k, type(v)))

    @staticmethod
    def _verify_bool(k, v, t):
        if v              in [True, False]       : return v
        if str(v).lower() in ['true', 'yes', '1']: return True
        if str(v).lower() in ['false', 'no', '0']: return False
        raise TypeError('expected bool type for %s (%s)' % (k, type(v)))

    _verifiers = {
            int  : _verify_int.__func__,
            str  : _verify_str.__func__,
            float: _verify_float.__func__,
            bool : _verify_bool.__func__,
    }

    _verifier_keys = list(_verifiers.keys())

    @classmethod
    def _verify_kvt(cls, k, v, t):

        if t is None              : return v
        if t in cls._verifier_keys: return cls._verifiers[t](k, v, t)
        if isinstance(t, dict)    : return cls._verify_dict(k, v, t)
        if isinstance(t, list)    : return cls._verify_list(k, v, t)
        print()
        print(t)
        print(isinstance(t, list))
        print(type(t))
        raise TypeError('no verifier defined for type %s' % t)

    @classmethod
    def _verify_list(cls, k, v, t):
        v = as_list(v)
        return [cls._verify_kvt(k + ' list element', _v, t[0]) for _v in v]

    @classmethod
    def _verify_dict(cls, k, v, t):
        t_k = list(t.keys())[0]
        t_v = list(t.values())[0]
        return {cls._verify_kvt(_k, _k, t_k) : cls._verify_kvt(_k, _v, t_v)
                                               for _k, _v in v.items()}
    def verify(self, schema):
        for k, v in self.items():
            if k not in schema: raise TypeError('key %s not in schema' % k)
            self[k] = self._verify_kvt(k, v, schema[k])
        self._verify()

    def _verify(self):
        '''
        Can be overloaded
        '''
        pass


# ------------------------------------------------------------------------------
#
class Description(Munch):
    '''
    This is an abstract base class for RCT description types.  Any inheriting
    class MUST provide a `self._schema` class member (not class instance member)
    which is used to verify the description's data validity.  Validation can be
    performed on request (`d.verify()`), or when setting description properties.
    The default is to verify on explicit calls only.
    '''

    # --------------------------------------------------------------------------
    #
    def __init__(self, from_dict=None, verify_setter=False):

        if not hasattr(self, '_schema'):
            raise RuntimeError('class %s has no schema defined' % self.__name__)

        super(Description, self).__init__(from_dict=from_dict)

        if verify_setter:
            raise NotImplemented('setter verification is not yet implemented')

        # TODO: setter verification should be done by attempting to cast the
        #       value to the target type and raising on failure.  Non-trivial
        #       types (lists, dicts) can use `as_list` and friends, or
        #       `isinstance` if that is not available
        #
        # TODO: setter verification should verify that the property is allowed


    # --------------------------------------------------------------------------
    #
    def verify(self):

        return super(Description, self).verify(self._schema)


# ------------------------------------------------------------------------------

