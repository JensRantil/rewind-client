# rewind-client talks to rewind, an event store server.
#
# Copyright (C) 2012  Jens Rantil
#
# This program is distributed under the MIT License. See the file LICENSE.txt
# for details.

"""Network clients used to communicate with the Rewind server."""
import logging

import zmq


logger = logging.getLogger(__name__)


class EventQuerier(object):

    """Client that queries events from rewind over ZeroMQ."""

    class QueryException(Exception):
        """Raised when rewind server returns an error.

        Usually this exception means you have used a non-existing query key.

        """
        pass

    def __init__(self, socket):
        """Constructor."""
        self.socket = socket

    def query(self, from_=None, to=None):
        """Make a query of events."""
        assert from_ is None or isinstance(from_, bytes)
        assert to is None or isinstance(to, bytes)
        first_msg = True
        done = False
        while not done:
            # _real_query(...) are giving us events in small batches
            done, events = self._real_query(from_, to)
            for eventid, eventdata in events:
                if first_msg:
                    assert eventid != from_, "First message ID wrong"
                    first_msg = False
                from_ = eventid
                yield (eventid, eventdata)

    def _real_query(self, from_, to):
        """Make the actual query for events.

        Since the Rewind streams events in batches, this method might not
        receive all requested events.

        Returns the tuple `(done, events)` where
         * `done` is a boolean whether the limited query result reached the
           end, or whether there's more events that need to be collected.
         * `events` is a list of `(eventid, eventdata)` event tuples where
          * `eventid` is a unique string the signifies the event; and
          * `eventdata` is a byte string containing the serialized event.

        """
        assert from_ is None or isinstance(from_, bytes), type(from_)
        assert to is None or isinstance(to, bytes), type(to)
        self.socket.send(b'QUERY', zmq.SNDMORE)
        self.socket.send(from_ if from_ else b'', zmq.SNDMORE)
        self.socket.send(to if to else b'')

        more = True
        done = False
        events = []
        while more:
            data = self.socket.recv()
            if data == b"END":
                assert not self.socket.getsockopt(zmq.RCVMORE)
                done = True
            elif data.startswith(b"ERROR"):
                assert not self.socket.getsockopt(zmq.RCVMORE)
                raise self.QueryException("Could not query: {0}".format(data))
            else:
                eventid = data
                assert isinstance(eventid, bytes), type(eventid)

                assert self.socket.getsockopt(zmq.RCVMORE)
                eventdata = self.socket.recv()

                eventtuple = (eventid, eventdata)
                events.append(eventtuple)

            if not self.socket.getsockopt(zmq.RCVMORE):
                more = False

        return done, events


def _get_single_streamed_event(streamsock):
    """Retrieve a streamed event off a socket.

    Parameters:
    streamsock -- the stream socket to be reading from.

    Returns a tuple consisting of:
        eventid     -- the ID of the streamed event
        lasteventid -- the ID of the previous streamed event. Can be empty for
                       the first event (which pretty much never happens)
        eventdata   -- the (serialized) data for the event.

    """
    eventid = streamsock.recv()
    assert streamsock.getsockopt(zmq.RCVMORE)
    lasteventid = streamsock.recv()
    assert streamsock.getsockopt(zmq.RCVMORE)
    eventdata = streamsock.recv()
    assert not streamsock.getsockopt(zmq.RCVMORE)
    return eventid, lasteventid, eventdata


def yield_events_after(streamsock, reqsock, lasteventid=None):
    """Generator that yields all the missed out events.

    Parameters:
    lasteventid -- the event id of the last seen event.

    TODO: Handle when there is no lasteventid.

    """
    assert lasteventid is None or isinstance(lasteventid, bytes)
    funclogger = logger.getChild('yield_events_after')

    cureventid, preveventid, evdata = _get_single_streamed_event(streamsock)

    if preveventid != lasteventid and preveventid != b'':
        # Making sure we did not reach high watermark inbetween here.

        msg = ('Seem to have reached high watermark. Doing manually querying'
               ' to catch up.')
        funclogger.info(msg)

        querier = EventQuerier(reqsock)
        for qeventid, qeventdata in querier.query(lasteventid, preveventid):
            # Note that this for loop's last event will be preveventid since
            # its last element is inclusive.
            yield qeventid, qeventdata

    yield cureventid, evdata


class EventPublisher(object):

    """Publishes events in a format that Rewind can understand."""

    def __init__(self, socket):
        """Constructor.

        Parameters:
        socket -- a ZeroMQ PUB socket connected to a Rewind instance.

        """
        self._socket = socket

    def send(self, event):
        """Send an event to Rewind.

        Parameters:
        event -- an event. Must be either `str` (Py2) or `bytes` (Py3).

        """
        assert isinstance(event, bytes), type(event)
        self._socket.send(event)

    def close(self):
        """Close the socket given to the constructor."""
        self._socket.close()
