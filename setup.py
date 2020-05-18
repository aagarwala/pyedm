from setuptools import setup

setup(
    name='main',
    version='0.1',
    py_modules=['pyedm.main'],
    install_requires=[
        'Click',
        'mutagen'
    ],
    entry_points='''
        [console_scripts]
        pyedm=pyedm.main:cli
    ''',
)
