<div align="right"><strong>RuMor: Russian Morphology project</strong></div>
<h2 align="center">Tuko: a tiny python NLP library for Russian text preprocessing</h2>

[![PyPI Version](https://img.shields.io/pypi/v/tuko?color=blue)](https://pypi.org/project/tuko/)
[![Python Version](https://img.shields.io/pypi/pyversions/tuko?color=blue)](https://www.python.org/)
[![License: BSD-3](https://img.shields.io/badge/License-BSD-brightgreen.svg)](https://opensource.org/licenses/BSD-3-Clause)

A part of ***RuMor*** project. It contains pipeline for preprocessing and
tokenization texts in *Russian*. Also, it includes preliminary entity tagging.
Highlights are:

* Extracting emojies, emails, dates, phones, urls, html/xml fragments etc.
* Taging/removing tokens with inallowed symbols
* Normalizing of punctuation
* Tokenization (via *NLTK*)
* Russan *Wikipedia* tokenizer

## Installation

### pip

***Tuko*** supports *Python 3.5* or later. To install it via *pip*, run:
```sh
$ pip install tuko
```

If you currently have a previous version of ***Tuko*** installed, use:
```sh
$ pip install tuko -U
```

### From Source

Alternatively, you can also install ***Tuko*** from source of this *git
repository*:
```sh
$ git clone https://github.com/fostroll/tuko.git
$ cd tuko
$ pip install -e .
```
This gives you access to examples that are not included to the *PyPI* package.

## Setup

***Tuko*** uses *NLTK* with *punkt* data downloaded. If you didn't do it yet,
start *Python* interpreter and execute:
```python
>>> import nltk
>>> nltk.download('punkt')
```

## Usage

[Text Preprocessor](https://github.com/fostroll/tuko/blob/master/doc/README_TEXT_PREPROCESSOR.md)

[Wrapper for tokenized *Wikipedia*](https://github.com/fostroll/tuko/blob/master/doc/README_WIKIPEDIA.md)

## Examples

You can find them in the directory `examples` of our github ***Tuko*** repository.

## License

***Tuko*** is released under the BSD License. See the
[LICENSE](https://github.com/fostroll/tuko/blob/master/LICENSE) file for more details.
