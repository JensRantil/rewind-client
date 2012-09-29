from setuptools import setup
import sys


py_version = sys.version_info[:2]
if py_version <= (2, 6):
    raise RuntimeError("Python <= 2.6 does not ship with argparse. "
                        "Therefore, rewind will not work with these.")


setup(
    name='rewind-client',
    version='0.1.0',
    author='Jens Rantil',
    author_email='jens.rantil@gmail.com',
    license='GNU AGPL, version 3',
    url='https://github.com/JensRantil/rewind-client',
    packages=[
        'rewind',
        'rewind.client',
        'rewind.client.test',
    ],
    namespace_packages=["rewind"],
    description='Python client for Rewind event store.',
    long_description=open('DESCRIPTION.rst').read(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: No Input/Output (Daemon)",
        "Intended Audience :: Other Audience",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.2",
        "Topic :: Software Development :: Object Brokering",
        "Topic :: System :: Distributed Computing",
    ],
    keywords="CQRS, event sourcing, ZeroMQ",
    setup_requires=[
        'nose>=1.0',
        'coverage==3.5.1',
    ],
    install_requires=[
        "pyzmq-static==2.1.11.2",
    ],
    tests_require=[
        "rewind==0.1.5",
        "mock==0.8",
        "pep8==1.3.3",
        "pep257==0.2.0",
    ],
    test_suite="rewind.client.test",
    entry_points={
        'console_scripts': [
            'rewind = rewind.server.rewind:main',
        ]
    },
)

