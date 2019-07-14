
__author__    = 'Radical.Utils Development Team (Andre Merzky)'
__copyright__ = 'Copyright 2013, RADICAL@Rutgers'
__license__   = 'MIT'

import radical.utils as ru


# ------------------------------------------------------------------------------
#
PLUGIN_DESCRIPTION = {
    'type'       : 'unittests_1',
    'name'       : 'default_2',
    'version'    : '0.1',
    'description': 'this is an empty test which basically does nothing.'
}


# ------------------------------------------------------------------------------
#
class PLUGIN_CLASS(object, metaclass=ru.Singleton):
    '''
    This class implements the (empty) default unittest plugin for radical.utils.
    '''

    _created = False  # singleton test


    # --------------------------------------------------------------------------
    #
    def __init__(self):

        if PLUGIN_CLASS._created:
            assert(False), 'singleton plugin should not get created twice'

        PLUGIN_CLASS._created = True


    # --------------------------------------------------------------------------
    #
    def init(self, arg1, arg2):

        self._arg1 = arg1
        self._arg2 = arg2


    # --------------------------------------------------------------------------
    #
    def run(self):

        return(self._arg2, self._arg1)


# ------------------------------------------------------------------------------

