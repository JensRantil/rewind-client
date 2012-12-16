# rewind-client talks to rewind, an event store server.
#
# Copyright (C) 2012  Jens Rantil
#
# This program is distributed under the MIT License. See the file LICENSE.txt
# for details.

"""Test overall Rewind execution."""
from __future__ import print_function

try:
    # Python < 3
    import ConfigParser as configparser
except ImportError:
    # Python >= 3
    import configparser
try:
    # Python < 3
    import StringIO as io
except ImportError:
    # Python >= 3
    import io
import threading
import time
import unittest
import uuid
import re

import mock
import zmq

import rewind.client as clients
import rewind.server.main as main


class _RewindRunnerThread(threading.Thread):

    """A thread that runs a rewind instance.

    While the thread is given command line arguments, Rewind is started as
    thread rather than external process. This makes it possible to check code
    coverage and track exit codes etc.

    """

    _EXIT_CODE = b'EXIT'

    def __init__(self, bootparams, exit_addr=None):
        """Constructor.

        Parameters:
        bootparams -- Can be either a dictionary of configuration options
                      grouped by section, or a list of command line argument
                      strings.
        exit_addr  -- the ZeroMQ address used to send the exit message to.

        """
        assert isinstance(bootparams, list) or isinstance(bootparams, dict)
        thread = self

        if isinstance(bootparams, list):
            assert '--exit-codeword' not in bootparams, \
                   ("'--exit-codeword' is added by _RewindRunnerThread."
                    " Not from elsewhere.")
            args = (main.main,
                    bootparams + ['--exit-codeword',
                                  _RewindRunnerThread._EXIT_CODE.decode()])
        else:
            assert isinstance(bootparams, dict)
            bootparams = dict(bootparams)

            if "general" not in bootparams:
                bootparams['general'] = {}
            EXCODE = _RewindRunnerThread._EXIT_CODE
            bootparams['general']['exit-code'] = EXCODE

            rows = []
            for section, keyvals in bootparams.items():
                rows.append("[{0}]".format(section))
                for key, val in keyvals.items():
                    rows.append("{0}={1}".format(key, val))

            configfilecontent = "\n".join(rows)
            options = configparser.SafeConfigParser()
            options.readfp(io.StringIO(configfilecontent))

            args = (main.run, options, _RewindRunnerThread._EXIT_CODE.decode())

        def exitcode_runner(func, *args, **kwargs):
            try:
                thread.exit_code = func(*args, **kwargs)
            except SystemExit as e:
                print("Runner made SystemExit.")
                thread.exit_code = e.code
            except Exception as e:
                print("Exception happened:", e)
                traceback.print_exc()
                thread.exit_code = None
            else:
                print("Clean exit of runner.")
        super(_RewindRunnerThread, self).__init__(target=exitcode_runner,
                                                  name="test-rewind",
                                                  args=args)
        self._exit_addr = exit_addr

    def stop(self, context=None):
        """Send a stop message to the event thread."""
        assert self._exit_addr is not None

        if context is None:
            context = zmq.Context(1)
        socket = context.socket(zmq.REQ)
        socket.connect(self._exit_addr)
        socket.send(_RewindRunnerThread._EXIT_CODE)
        time.sleep(0.5)  # Acceptable exit time
        assert not self.isAlive()
        socket.close()


class TestReplication(unittest.TestCase):

    """Test high-level replication behaviour."""

    UUID_REGEXP = ("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-"
                   "[0-9a-f]{12}")

    def setUp(self):
        """Starting a Rewind instance to test replication."""
        args = {
            'general': {
                'query-bind-endpoint': 'tcp://127.0.0.1:8090',
                'streaming-bind-endpoint': 'tcp://127.0.0.1:8091',
            }
        }
        self.rewind = _RewindRunnerThread(args, 'tcp://127.0.0.1:8090')
        self.rewind.start()

        self.context = zmq.Context(3)

        self.transmitter = self.context.socket(zmq.REQ)
        self.transmitter.connect('tcp://127.0.0.1:8090')

        # Making sure context.term() does not time out
        # Could be removed if this test works as expected
        self.transmitter.setsockopt(zmq.LINGER, 1000)

        self.receiver = self.context.socket(zmq.SUB)
        self.receiver.setsockopt(zmq.SUBSCRIBE, b'')
        self.receiver.connect('tcp://127.0.0.1:8091')

        # Time it takes to connect. This is particularly important so that the
        # receiver does not just receive the tail of the stream.
        time.sleep(0.5)

    def testBasicEventProxying(self):
        """Asserting a single event is proxied."""
        eventstring = b"THIS IS AN EVENT"

        clients.publish_event(self.transmitter, eventstring)

        received_id = self.receiver.recv().decode()
        self.assertTrue(bool(self.receiver.getsockopt(zmq.RCVMORE)))
        prev_received_id = self.receiver.recv()
        self.assertEquals(prev_received_id, b'')
        self.assertTrue(bool(self.receiver.getsockopt(zmq.RCVMORE)))
        received_string = self.receiver.recv()
        self.assertFalse(bool(self.receiver.getsockopt(zmq.RCVMORE)))

        self.assertIsNotNone(re.match(self.UUID_REGEXP, received_id))
        self.assertEqual(received_string, eventstring)

    def testProxyingABunchOfEvents(self):
        """Testing that a bunch of incoming messages processed correctly.

        That is, they are all being proxied and in order.

        """
        NMESSAGES = 200
        messages = []
        for id in range(NMESSAGES):
            eventstring = "THIS IS EVENT NUMBER {0}".format(id).encode()
            messages.append(eventstring)

        # Sending
        for msg in messages:
            clients.publish_event(self.transmitter, msg)

        # Receiving and asserting correct messages
        eventids = []
        received_messages = []
        previd = b''
        for msg in messages:
            received_id = self.receiver.recv()
            self.assertTrue(bool(self.receiver.getsockopt(zmq.RCVMORE)))
            received_prev_id = self.receiver.recv()

            self.assertEquals(received_prev_id, previd)
            previd = received_id

            self.assertTrue(bool(self.receiver.getsockopt(zmq.RCVMORE)))
            received_string = self.receiver.recv()
            received_messages.append(received_string)
            self.assertFalse(bool(self.receiver.getsockopt(zmq.RCVMORE)))
            self.assertIsNotNone(re.match(self.UUID_REGEXP,
                                          received_id.decode()))
            eventids.append(received_id)
            self.assertEqual(received_string, msg)

        self.assertEqual(len(set(eventids)), len(eventids),
                         "Found duplicate event id!")
        self.assertEqual(messages, received_messages,
                         "Not all messages received")

    def tearDown(self):
        """Shutting down Rewind test instance."""
        self.transmitter.close()
        self.receiver.close()

        self.assertTrue(self.rewind.isAlive(),
                        "Did rewind crash? Not running.")
        self.rewind.stop(self.context)
        self.assertFalse(self.rewind.isAlive(),
                         "Rewind should not have been running. It was.")

        self.context.term()


class TestQuerying(unittest.TestCase):

    """Test high-level event querying behaviour."""

    def setUp(self):
        """Start and populate a Rewind instance to test querying."""
        args = {
            'general': {
                'query-bind-endpoint': 'tcp://127.0.0.1:8090',
            }
        }
        self.rewind = _RewindRunnerThread(args, 'tcp://127.0.0.1:8090')
        self.rewind.start()

        self.context = zmq.Context(3)

        self.querysock = self.context.socket(zmq.REQ)
        self.querysock.connect('tcp://127.0.0.1:8090')

        ids = [uuid.uuid1().hex for i in range(200)]
        self.assertEqual(len(ids), len(set(ids)), 'There were duplicate IDs.'
                         ' Maybe the UUID1 algorithm is flawed?')
        users = [uuid.uuid1().hex for i in range(30)]
        self.assertEqual(len(users), len(set(users)),
                         'There were duplicate users.'
                         ' Maybe the UUID1 algorithm is flawed?')

        self.sent = []
        for id in ids:
            eventstr = "Event with id '{0}'".format(id).encode()
            self.querysock.send(b"PUBLISH", zmq.SNDMORE)
            self.querysock.send(eventstr)
            response = self.querysock.recv()
            assert response == b'PUBLISHED'
            assert not self.querysock.getsockopt(zmq.RCVMORE)
            self.sent.append(eventstr)

    def testSyncAllPastEvents(self):
        """Test querying all events."""
        time.sleep(0.5)  # Max time to persist the messages
        allevents = [event[1]
                     for event in clients.query_events(self.querysock)]
        self.assertEqual(allevents, self.sent)

        self.assertEqual(allevents, self.sent, "Elements don't match.")

    def testSyncEventsSince(self):
        """Test querying events after a certain time."""
        time.sleep(0.5)  # Max time to persist the messages
        allevents = [event for event in clients.query_events(self.querysock)]
        from_ = allevents[3][0]
        events = [event[1] for event in clients.query_events(self.querysock,
                                                             from_=from_)]
        self.assertEqual([event[1] for event in allevents[4:]], events)

    def testSyncEventsBefore(self):
        """Test querying events before a certain time."""
        time.sleep(0.5)  # Max time to persist the messages
        allevents = [event
                     for event in clients.query_events(self.querysock)]
        to = allevents[-3][0]
        events = [event[1]
                  for event in clients.query_events(self.querysock, to=to)]
        self.assertEqual([event[1] for event in allevents[:-2]], events)

    def testSyncEventsBetween(self):
        """Test querying events a slice of the events."""
        time.sleep(0.5)  # Max time to persist the messages
        allevents = [event for event in clients.query_events(self.querysock)]
        from_ = allevents[3][0]
        to = allevents[-3][0]
        events = [event[1]
                  for event in clients.query_events(self.querysock,
                                                    from_=from_,
                                                    to=to)]
        self.assertEqual([event[1] for event in allevents[4:-2]], events)

    def testSyncNontExistentEvent(self):
        """Test when querying for non-existent event id."""
        result = clients.query_events(self.querysock, from_=b"non-exist")
        self.assertRaises(clients.QueryException,
                          list, result)

    def tearDown(self):
        """Close Rewind test instance."""
        self.querysock.close()

        self.assertTrue(self.rewind.isAlive(),
                        "Did rewind crash? Not running.")
        self.rewind.stop(self.context)
        self.assertFalse(self.rewind.isAlive(),
                         "Rewind should not have been running. It was.")

        self.context.term()


class TestEventReception(unittest.TestCase):

    """Test event reception using `yield_events_after`."""

    def setUp(self):
        """Set up the each test."""
        self.events = [
            (b'a', b'', b'event1'),
            (b'b', b'a', b'event2'),
            (b'c', b'b', b'event3'),
        ]

    def testRecvFirstEvent(self):
        """Test fetching the absolutely first event."""
        streamsock = mock.NonCallableMock()
        streamsock.recv.side_effect = self.events[0]
        streamsock.getsockopt.side_effect = [True, True, False, False]

        reqsock = mock.NonCallableMock()

        results = []
        for result in clients.yield_events_after(streamsock, reqsock):
            results.append(result)
        self.assertEqual(results, [(self.events[0][0], self.events[0][2])])
        assert streamsock.recv.called
        assert not reqsock.recv.called

    def testRecvNonFloodedNextEvent(self):
        """Test receiving the next event through streaming socket only."""
        streamsock = mock.NonCallableMock()
        streamsock.recv.side_effect = self.events[2]
        streamsock.getsockopt.side_effect = [True, True, False]

        reqsock = mock.NonCallableMock()

        results = []
        for result in clients.yield_events_after(streamsock, reqsock,
                                                 self.events[1][0]):
            results.append(result)
        self.assertEqual(results, [(self.events[2][0], self.events[2][2])])
        assert streamsock.recv.called
        assert not reqsock.recv.called

    def testRecvFloodedSocket(self):
        """Test receiving an event when watermark was passed."""
        streamsock = mock.NonCallableMock()
        streamsock.recv.side_effect = self.events[2]
        streamsock.getsockopt.side_effect = [True, True, False]

        reqsock = mock.NonCallableMock()
        toreceive = (self.events[1][0], self.events[1][2], b'END')
        reqsock.recv.side_effect = toreceive
        # Need two 'False' here due to assertion logic in query code
        reqsock.getsockopt.side_effect = [True, True, False, False]

        results = []
        for result in clients.yield_events_after(streamsock, reqsock,
                                                 self.events[0][0]):
            results.append(result)

        # Implementation specific tests that have been used mostly for
        # debugging of the code. Can be removed without being too worried.
        assert not streamsock.send.called
        reqsock.send.assert_has_calls([mock.call(b"QUERY", zmq.SNDMORE),
                                       mock.call(self.events[0][0],
                                                 zmq.SNDMORE),
                                       mock.call(self.events[1][0])])
        self.assertEqual(streamsock.recv.call_count, 3,
                         streamsock.recv.call_args_list)
        self.assertEqual(reqsock.recv.call_count, 3)

        # The actual test that makes sure result is what it's supposed to be.
        self.assertEqual(results, [(self.events[1][0], self.events[1][2]),
                                   (self.events[2][0], self.events[2][2])])
