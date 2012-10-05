=============
Rewind Client
=============

.. image:: https://secure.travis-ci.org/JensRantil/rewind-client.png?branch=develop
   :target: http://travis-ci.org/#!/JensRantil/rewind-client

This is a Python client that talks to the `Rewind`_ event sourcing server.

.. _Rewind: https://github.com/JensRantil/rewind

Installing
==========

PyPi
----
``rewind-client`` `exists on PyPi`_. You can install it by issuing::

    $ pip install rewind-client

Do NOTE, however, that this will install the client in global Python
space. See documentation on `virtualenv` below on how to not do this.

.. _exists on PyPi: http://pypi.python.org/pypi/rewind-client/

Manual install
--------------
``rewind-client`` uses basic ``setuptools``. Installation can be used done as
follows::

    $ git clone https://github.com/JensRantil/rewind-client.git
    $ cd rewind-client
    $ python setup.py install

However, **NOTE** that this will install Rewind client globally in your
Python environment and is NOT recommended. Please refer to virtualenv_
on how to create a virtual environment.

.. _virtualenv: http://www.virtualenv.org

Using the client
================
STUB.

Developing
==========
Getting started developing ``rewind-client`` is quite straightforward. The
library uses ``setuptools`` and standard Python project layout for tests
etcetera.

Checking out
------------
To start developing you need to install the ZeroMQ library on your system
beforehand.

This is how you check out the ``rewind-client`` library into a virtual
environment::

    cd <your development directory>
    virtualenv --no-site-packages rewind-client
    cd rewind-client
    git clone http://<rewind GIT URL> src

Workin' the code
----------------
Every time you want to work on ``rewind-client`` you want to change
directory into the source folder and activate the virtual environment
scope (so that you don't touch the global Python environment)::

    cd src
    source ../bin/activate

The first time you've checked the project out, you want to initialize
development mode::

    python setup.py develop

Runnin' them tests
------------------
Running the test suite is done by issuing::

    python setup.py nosetests

. Nose is configured to automagically spit out test coverage information
after the whole test suite has been executed.

As always, try to run the test suite *before* starting to mess with the
code. That way you know nothing was broken beforehand.

`The Rewind client central github repository`_ also has Travis CI
integration that can be accessed at
http://travis-ci.org/#!/JensRantil/rewind-client Every time a pull request is
being made to https://github.com/JensRantil/rewind-client, Travis CI will make
a commend about whether the pull request breaks the test suite or not.

.. _The Rewind client central github repository: https://github.com/JensRantil/rewind-client
.. _Travis CI: http://travis-ci.org

Helping out
===========
Spelling mistakes, bad grammar, wire format improvements, test
improvements and other feature additions are all welcome. Please issue
pull requests or create an issue if you'd like to discuss it on Github.

Author
======

This package has been developed by Jens Rantil <jens.rantil@gmail.com>.
You can also reach me through snailmail at::

    Jens Rantil
    Lilla Södergatan 6A
    22353 Lund
    SWEDEN
