
import os
import csv
import glob
import time
import threading

from   .misc      import name2env     as ru_name2env
from   .misc      import get_hostname as ru_get_hostname
from   .misc      import get_ip       as ru_get_ip
from   .read_json import read_json    as ru_read_json


# ------------------------------------------------------------------------------
#
_prof_fields  = ['time', 'name', 'uid', 'state', 'event', 'msg']


# ------------------------------------------------------------------------------
#
class Profiler(object):
    """
    This class is really just a persistent file handle with a convenience call
    (prof()) to write lines with timestamp and events.
    Any profiling intelligence is applied when reading and evaluating the 
    created profiles.
    """

    # --------------------------------------------------------------------------
    #
    def __init__(self, name, env_name=None, path=None):

        # this init is only called once (globally).  We synchronize clocks and
        # set timestamp_zero
        if not env_name:
            env_name = '%s_PROFILE' % ru_name2env(name)

        self._handles = dict()

        # we only profile if so instructed
        if env_name in os.environ:
            self._enabled = True
        else:
            self._enabled = False
            return


        self._ts_zero, self._ts_abs, self._ts_mode = self._timestamp_init()


        if not path:
            path = os.getcwd()

        self._path = path
        self._name = name

        try:
            os.makedirs(self._path)
        except OSError:
            pass # already exists

        self._handle = open("%s/%s.prof" % (self._path, self._name), 'a')

        # write header and time normalization info
        self._handle.write("#%s\n" % (','.join(_prof_fields)))
        self._handle.write("%.4f,%s:%s,%s,%s,%s,%s\n" % \
                           (self.timestamp(), self._name, "", "", "", 'sync abs',
                            "%s:%s:%s:%s:%s" % (
                                ru_get_hostname(), ru_get_hostip(),
                                self._ts_zero, self._ts_abs, self._ts_mode)))


    # ------------------------------------------------------------------------------
    #
    @property
    def enabled(self):

        return self._enabled


    # ------------------------------------------------------------------------------
    #
    def close(self):

        if not self._enabled:
            return

        if self._enabled:
            self.prof("END")
            self._handle.close()


    # ------------------------------------------------------------------------------
    #
    def flush(self):

        if not self._enabled:
            return

        if self._enabled:
            # see https://docs.python.org/2/library/stdtypes.html#file.flush
            self.prof("flush")
            self._handle.flush()
            os.fsync(self._handle.fileno())


    # ------------------------------------------------------------------------------
    #
    def prof(self, event, uid=None, state=None, msg=None, timestamp=None, logger=None):

        if not self._enabled:
            return

        if not timestamp:
            timestamp = self.timestamp()

        # if uid is a list, then recursively call self.prof for each uid given
        if isinstance(uid, list):
            for _uid in uid:
                self.prof(event, _uid, state, msg, timestamp, logger)
            return

        if logger:
            logger("%s (%10s%s) : %s", event, uid, state, msg)

        tid = threading.current_thread().name

        if None == uid  : uid   = ''
        if None == msg  : msg   = ''
        if None == state: state = ''

        self._handle.write("%.4f,%s:%s,%s,%s,%s,%s\n" \
                % (timestamp, self._name, tid, uid, state, event, msg))


    # --------------------------------------------------------------------------
    #
    def _timestamp_init(self):
        """
        return a tuple of [system time, absolute time]
        """

        # retrieve absolute timestamp from an external source
        #
        # We first try to contact a network time service for a timestamp, if that
        # fails we use the current system time.
        try:
            import ntplib

            ntphost = os.environ.get('RADICAL_UTILS_NTPHOST', '0.pool.ntp.org')

            t_one = time.time()
            response = ntplib.NTPClient().request(ntphost, timeout=1)
            t_two = time.time()

            ts_ntp = response.tx_time
            ts_sys = (t_one + t_two) / 2.0
            return [ts_sys, ts_ntp, 'ntp']

        except Exception:
            pass

        # on any errors, we fall back to system time
        t = time.time()
        return [t,t, 'sys']


    # --------------------------------------------------------------------------
    #
    def timestamp(self):

        return time.time()


# --------------------------------------------------------------------------
#
def timestamp():

    return time.time()


# ------------------------------------------------------------------------------
#
def read_profiles(profiles):
    """
    We read all profiles as CSV files and convert them into lists of dicts.
    """
    ret = dict()

    for prof in profiles:
        rows = list()
        with open(prof, 'r') as csvfile:
            reader = csv.DictReader(csvfile, fieldnames=_prof_fields)
            for row in reader:

                if row['time'].startswith('#'):
                    # skip header
                    continue

                row['time'] = float(row['time'])
                rows.append(row)
    
        ret[prof] = rows

    return ret


# ------------------------------------------------------------------------------
#
def combine_profiles(profs):
    """
    We merge all profiles and sort by time.

    This routine expects all profiles to have a synchronization time stamp.
    Two kinds of sync timestamps are supported: absolute (`sync abs`) and 
    relative (`sync rel`).

    Time syncing is done based on 'sync abs' timestamps.  We expect one such
    absolute timestamp to be available per host (the first profile entry will
    contain host information).  All timestamps from the same host will be
    corrected by the respectively determined NTP offset.
    """

    pd_rel = dict() # profiles which have relative time refs
    t_host = dict() # time offset per host
    p_glob = list() # global profile
    t_min  = None   # absolute starting point of profiled session
    c_end  = 0      # counter for profile closing tag

    # first get all absolute timestamp sync from the profiles, for all hosts
    for pname, prof in profs.iteritems():

        if not len(prof):
            print 'empty profile %s' % pname
            continue

        if not prof[0]['msg'] or not ':' in if not prof[0]['msg']:
            print 'unsynced profile %s' % pname
            continue

        t_prof = prof[0]['time']

        host, ip, t_sys, t_ntp, t_mode = prof[0]['msg'].split(':')
        host_id = '%s:%s' % (host, ip)

        if t_min: t_min = min(t_min, t_prof)
        else    : t_min = t_prof

        if t_mode != 'sys':
            continue

        # determine the correction for the given host
        t_sys = float(t_sys)
        t_ntp = float(t_ntp)
        t_off = t_sys - t_ntp

        if host_id in t_host and t_host[host_id] != t_off:
            print 'conflicting time sync for %s (%s)' % (pname, host_id)
            continue

        t_host[host_id] = t_off


    # now that we can align clocks for all hosts, apply that correction to all
    # profiles
    for pname, prof in profs.iteritems():

        if not len(prof):
            continue

        if not prof[0]['msg']:
            continue

        host, ip, _, _, _ = prof[0]['msg'].split(':')
        host_id = '%s:%s' % (host, ip)
        if host_id in t_host:
            t_off = t_host[host_id]
        else:
            print 'WARNING: no time offset for %s' % host_id
            t_off = 0.0

        t_0 = prof[0]['time']
        t_0 -= t_min

        # correct profile timestamps
        for row in prof:

            t_orig = row['time'] 

            row['time'] -= t_min
            row['time'] -= t_off

            # count closing entries
            if row['event'] == 'END':
                c_end += 1

        # add profile to global one
        p_glob += prof


      # # Check for proper closure of profiling files
      # if c_end == 0:
      #     print 'WARNING: profile "%s" not correctly closed.' % prof
      # if c_end > 1:
      #     print 'WARNING: profile "%s" closed %d times.' % (prof, c_end)

    # sort by time and return
    p_glob = sorted(p_glob[:], key=lambda k: k['time']) 

    return p_glob


# ------------------------------------------------------------------------------
# 
def clean_profile(profile, sid, state_final, state_canceled):
    """
    This method will prepare a profile for consumption in radical.analytics.  It
    performs the following actions:

      - makes sure all events have a `ename` entry
      - remove all state transitions to `CANCELLED` if a different final state 
        is encountered for the same uid
      - assignes the session uid to all events without uid
      - makes sure that state transitions have an `ename` set to `state`
    """

    entities = dict()  # things which have a uid

    if not isinstance(state_final, list):
        state_final = [state_final]

    for event in profile:
        uid   = event['uid'  ]
        state = event['state']
        time  = event['time' ]
        name  = event['event']

        # we derive entity_type from the uid -- but funnel 
        # some cases into the session
        if uid:
            event['entity_type'] = uid.split('.',1)[0]
        else:
            event['entity_type'] = 'session'
            event['uid']         = sid
            uid = sid

        if uid not in entities:
            entities[uid] = dict()
            entities[uid]['states'] = dict()
            entities[uid]['events'] = list()

        if name == 'advance':

            # this is a state progression
            assert(state)
            assert(uid)

            event['event_name'] = 'state'

            if state in state_final and state != state_canceled:

                # a final state other than CANCELED will cancel any previous 
                # CANCELED state.  
                if state_canceled in entities[uid]['states']:
                   del(entities[uid]['states'][state_canceled])

            if state in entities[uid]['states']:
                # ignore duplicated recordings of state transitions
                # FIXME: warning?
                continue
              # raise ValueError('double state (%s) for %s' % (state, uid))

            entities[uid]['states'][state] = event

        else:
            # FIXME: define different event types (we have that somewhere)
            event['event_name'] = 'event'

        entities[uid]['events'].append(event)


    # we have evaluated, cleaned and sorted all events -- now we recreate
    # a clean profile out of them
    ret = list()
    for uid,entity in entities.iteritems():

        ret += entity['events']
        for state,event in entity['states'].iteritems():
            ret.append(event)

    # sort by time and return
    ret = sorted(ret[:], key=lambda k: k['time']) 

    return ret


# ------------------------------------------------------------------------------

