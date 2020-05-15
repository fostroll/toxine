import os
from setuptools import setup, find_packages

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
version_file_contents = open(os.path.join(SCRIPT_DIR, 'toxine/_version.py'),
                             'rt', encoding='utf-8').read()
VERSION = version_file_contents.strip()[len('__version__ = "'):-1]

setup(
    name='toxine',
    version=VERSION,
    description='Tiny preprocessor for Russian text',
    long_description=open('README.md', 'rt', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    author='Sergei Ternovykh',
    author_email='fostroll@gmail.com',
    url='https://github.com/fostroll/toxine',
    license='BSD',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',
        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Information Technology',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Text Processing',
        'Topic :: Text Processing :: Linguistic',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries',
        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    # What does your project relate to?
    keywords='natural-language-processing nlp preprocessing',

    packages=find_packages(exclude=['data', 'doc', 'examples', 'scripts',
                                    'tests']),
    install_requires=['corpuscula', 'nltk', 'pymorphy2'],
    include_package_data=True,
    python_requires='>=3.5',
)
