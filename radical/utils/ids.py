

import random
import datetime
import threading


# ------------------------------------------------------------------------------
#
_rlock = threading.RLock ()

with _rlock :
    _id_cnts = {}
    

# ------------------------------------------------------------------------------
#
def generate_id (idtype) :

    with _rlock :

        global _id_cnts

        now = datetime.datetime.utcnow ()

        if  not idtype in _id_cnts :
            _id_cnts[idtype] =  1
        else :
            _id_cnts[idtype] += 1

        xid_date = "%04d%02d%02d" % (now.year, now.month,  now.day)
        xid_time = "%02d%02d%02d" % (now.hour, now.minute, now.second)
        xid_seq  = "%04d"         % (_id_cnts[idtype])

      # FIXME: make format more configurable
      # xid = "%s.%s.%s.%s" % (idtype, xid_date, xid_time, xid_seq)
        xid = "%s%s"        % (idtype,                     xid_seq)

        return str(xid)


# ------------------------------------------------------------------------------
#
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
