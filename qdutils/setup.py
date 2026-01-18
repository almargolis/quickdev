from setuptools import setup

setup(
    name="qdutils",
    version="0.1.0",
    author="Albert Margolis",
    description="QuickDev command-line utilities",
    package_dir={'': 'src'},
    packages=['qdutils'],
    install_requires=[
        "qdbase>=0.2.0",
        "qdcore>=0.1.0",
    ],
    entry_points={
        'console_scripts': [
            'qdo=qdutils.qdo:main',
            'qdstart=qdutils.qdstart:main',
            'xsynth=qdutils.xsynth:main',
        ],
    },
    python_requires=">=3.7",
)
