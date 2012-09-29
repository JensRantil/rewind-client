# rewind-client talks to rewind, an event store server.
#
# Copyright (C) 2012  Jens Rantil
#
# This program is distributed under the MIT License. See the file LICENSE.txt
# for details.

"""Test code format and coding standards."""
from __future__ import print_function
import os
import pep8
import pep257
import unittest


class TestCodeFormat(unittest.TestCase):

    """Tests that asserts code quality."""

    @classmethod
    def setUpClass(cls):
        """Create a list of all Python files in Rewind."""
        cls._pyfiles = cls._get_all_pyfiles()

    @staticmethod
    def _get_all_pyfiles():
        """Return a list of all Python files in Rewind."""
        pyfiles = []
        for dirpath, _, filenames in os.walk('rewind'):
            pyfiles.extend([os.path.join(dirpath, filename)
                            for filename in filenames
                            if filename.endswith('.py')])
        return pyfiles

    def testPep8Conformance(self):
        """Test that we conform to PEP8."""
        pep8style = pep8.StyleGuide()
        result = pep8style.check_files(self._pyfiles)

        # Currently two E301:s fail. I find those checks to be
        # buggy and will report them to the pep8 project on github.
        self.assertEqual(result.total_errors, 0,
                         "Found code syntax errors (and warnings).")

    def testPep257Conformance(self):
        """Test that we conform to PEP257."""
        errors = pep257.check_files(self._pyfiles)
        if errors:
            print("There were errors:")
            for error in errors:
                print(error)
        self.assertEquals(len(errors), 0)

    def testLogbookIsGone(self):
        """Make sure we no longer use the name "logbook".

        "logbook" was the early working project name that later became
        "rewind".

        """
        errmsg = "'{0}' contained 'logbook' although it shouldn't"
        for pyfile in self._pyfiles:
            if pyfile.endswith('/test_code.py'):
                continue
            with open(pyfile) as f:
                pythoncode = f.read()
            assert "logbook" not in pythoncode.lower(), errmsg.format(pyfile)

    def test_license_header(self):
        """Testing all source files contains license header."""
        needle = "MIT License"
        for pyfile in self._pyfiles:
            with open(pyfile) as f:
                haystack = f.read()
                msg = "{0} did not contain license header"
                self.assertTrue(needle in haystack, msg.format(pyfile))
