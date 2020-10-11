import pickle
import os
from typing import List
from nltk import word_tokenize
import re

P = re.compile(r'(\d+)')  # regex for masking numbers


def get_wd():
    """
    :return: the current working directory
    """
    return os.path.dirname(os.path.realpath(__file__))


def tokenize(text, tokenizer=word_tokenize, *args, **kwargs):
    """
    Tokenize the text with the given tokenizer.
    Records are split on newlines and then the tokenizer is applied to each line.
    :param tokenizer: tokenization function
    :param args: arguments for the tokenization function
    :param kwargs: keyword arguments for the tokenization function
    :return: dict of masked numbers, list of lists of tokens
    """
    lines = []
    numbers = {}
    for ln, line in enumerate(text.split('\n')):
        toks = tokenizer(line.lower(), *args, **kwargs)
        for i, t in enumerate(toks):
            nums = P.findall(t)
            toks[i] = P.sub('D', t)

            # save masked numbers so they can be recovered later
            if nums:
                numbers[(ln, i)] = tuple(nums)

        lines.append(toks)

    return numbers, lines


class Tag:
    __slots__ = 'line', 'id', 'class_', 'token'
    REG = 'regular'
    AMB = 'ambiguous'
    FUZ = 'fuzzy'

    def __init__(self, line, idx, token, class_=REG):
        """
        Tag helper class.

        :param line: line number
        :param idx: position in line
        :param token: token text
        :param class_: tag class (regular, fuzzy, or ambiguous)
        """
        self.line = line
        self.id = idx
        self.class_ = class_
        self.token = token

    def __repr__(self):
        return f'({self.line},{self.id}): {self.token} - {self.class_}'


class Record:
    __slots__ = 'id', 'tokens', 'tags', 'numbers'

    def __init__(self, id_, text, tokenizer=word_tokenize):
        """
        Record helper class.
        Tokenizes the text and masks numbers, keeps track of tags.

        :param id_: record id
        :param text: raw record text
        :param tokenizer: tokenization function
        """
        self.id = id_
        self.numbers, self.tokens = tokenize(text, tokenizer=tokenizer)
        self.tags = {}

    def get_tag(self, line, idx):
        if (line, idx) in self.tags:
            return self.tags[(line, idx)]
        else:
            return None

    def __repr__(self):
        return f'Record({self.id})'


class Records(List):
    def __init__(self, iterable=()):
        super().__init__(iterable)

    def save(self, path=get_wd() + '/data/records.pickle'):
        """
        Save the records as a pickle file.
        :param path: save location
        """
        with open(path, 'wb') as file:
            pickle.dump(self, file)

    def load(self,  path=get_wd() + '/data/records.pickle'):
        """
        Load records saved by the save method.
        :param path: save file location
        """
        with open(path, 'rb') as file:
            self.extend(pickle.load(file))


class LexiconEntry:
    __slots__ = 'entry', 'raw', 'class_', 'parent', 'numbers'

    def __init__(self, entry, raw, numbers=None, class_=Tag.REG, parent=None):
        """
        Lexicon entry helper class.

        :param entry: tokenized entry
        :param raw: human-readable entry
        :param numbers: masked numbers
        :param class_: entry type (regular, fuzzy, or ambiguous)
        :param parent: tokenized parent entry (for fuzzy matches)
        """
        self.entry = entry
        self.raw = raw
        self.class_ = class_
        self.parent = parent
        self.numbers = numbers

    def __repr__(self):
        return self.raw


def records_from_pickle(path=get_wd() + '/data/records.pickle'):
    """
    Load records as saved by the Records.save function.

    :param path: pickle file location
    :return: list of records
    """
    records = Records()
    records.load(path)

    return records


def build_lexicon(path=get_wd() + '/data/lexicon.txt', tokenizer=word_tokenize, encoding='utf-8'):
    """
    Read a text file with a single lexicon entry per line.

    :param path: text file location
    :param tokenizer: tokenization function
    :param encoding: text file encoding
    :return: {(tokens): LexiconEntry} dictionary
    """
    lexicon = {}
    with open(path, 'r', encoding=encoding) as file:
        for line in file.readlines():
            nums = P.findall(line)
            tok = tuple(tokenizer(P.sub('D', line)))
            lexicon[tok] = LexiconEntry(tok, line.strip(), nums)

    return lexicon
