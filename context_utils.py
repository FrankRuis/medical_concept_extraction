from collections import Counter

from fuzzy import get_fuzzy_matches, get_fuzzy_matches_multi, calculate_pmi
from data_utils import LexiconEntry, Tag, get_wd
import pickle
from gui import ReviewGUI


def get_at_n(tokens, line, pos, n, lexicon=()):
    if pos + n < 0:
        if line == 0:
            return ''
        else:
            npos = pos + n
            tok = tokens[line - 1][npos] if tokens[line - 1] and abs(npos) <= len(tokens[line - 1]) else ''
            return tok if tok not in lexicon else 'M'
    elif pos + n >= len(tokens[line]):
        if line + 1 == len(tokens):
            return ''
        else:
            npos = pos + n - len(tokens[line])
            tok = tokens[line + 1][npos] if tokens[line + 1] and npos < len(tokens[line + 1]) else ''
            return tok if tok not in lexicon else 'M'
    else:
        tok = tokens[line][pos + n] if tokens[line] else ''
        return tok if tok not in lexicon else 'M'


class CandidateFinder:
    def __init__(self, records, lexicon=None, window=3, rejected=None):
        self.records = records
        self.words = list({word for record in records for sentence in record.tokens for word in sentence if len(word) > 1})
        self.pmi = calculate_pmi(records)
        self.lexicon = lexicon
        self.window = window
        self.candidates = []
        self.contexts = None
        self.pos_counter = None
        self.pos_counter_m = None
        if not rejected:
            self.rejected = set()

    def _score_context(self, context) -> float:
        """
        Calculates the partial match score as described in the paper.

        :param context: context to calculate the score for
        :return: partial match score
        """
        cur = 0
        for i, e in enumerate(context):
            cur += self.pos_counter_m[(i, e)] / self.pos_counter[(i, e)]

        return cur / 6

    def process_contexts(self, thresh=0.25, partial=0.25, min_count=1) -> None:
        """
        Find and filter all lexicon match contexts and calculate necessary statistics for the partial match score.

        :param thresh: certainty threshold
        :param partial: partial match threshold
        :param min_count: minimum occurrence count to keep a context
        """
        gc = Counter()  # global context counter
        contexts = Counter()  # match context counter
        for record in self.records:
            tokens = record.tokens
            for ln, line in enumerate(tokens):
                for i, w in enumerate(line):
                    # look at up to 3 tokens in the middle
                    for l in range(3):
                        # stop if a sentence boundary is reached or there is a 1 character token
                        if i + l >= len(tokens[ln]) or len(tokens[ln][i + l]) < 2:
                            break
                        toks = tuple(line[i + m] for m in range(l + 1))  # tokens in the middle
                        tpl = tuple([get_at_n(tokens, ln, i if k < 0 else i + l, k, self.lexicon) for k in
                                     range(-self.window, self.window + 1) if k != 0])  # context surrounding the tokens
                        gc[tpl] += 1
                        if toks in self.lexicon:
                            contexts[tpl] += 1

        # filter the contexts on certainty score and minimum occurrence count
        # also filter if the context exclusively surrounds known lexicon entries
        filtered_contexts = {c: contexts[c] for c in contexts if
                             c in gc and contexts[c] / gc[c] > thresh and contexts[c] != gc[c] and contexts[
                                 c] > min_count}

        # calculate position statistics for partial match score
        pos_counter = Counter()
        for c in gc:
            for i, e in enumerate(c):
                pos_counter[(i, e)] += 1

        pos_counter_m = Counter()
        for c in filtered_contexts:
            for i, e in enumerate(c):
                pos_counter_m[(i, e)] += 1

        # add contexts that exceed the partial match threshold
        self.pos_counter = pos_counter
        self.pos_counter_m = pos_counter_m
        for c in gc:
            if c in contexts:
                continue

            if self._score_context(c) > partial:
                filtered_contexts[c] = 1

        self.contexts = filtered_contexts

    def get_candidates(self) -> list:
        """
        Finds all candidate entries surrounded by a valid match context.

        :return: list of (candidate, context) tuples
        """
        candidates = []
        cdc = Counter()
        for record in self.records:
            tokens = record.tokens
            for line in range(len(tokens)):
                for pos in range(len(tokens[line])):
                    tok = tokens[line][pos]
                    if len(tok) < 2 or tok in self.lexicon:
                        continue

                    # look at up to 3 tokens in the middle
                    for l in range(3):
                        # stop if a sentence boundary is reached or there is a 1 character token
                        if pos + l >= len(tokens[line]) or len(tokens[line][pos + l]) < 2:
                            break

                        tpl = tuple([get_at_n(tokens, line, pos if k < 0 else pos + l, k, self.lexicon) for k in
                                     range(-self.window, self.window + 1) if k != 0])  # context
                        if tpl in self.contexts:
                            candidate = tuple([get_at_n(tokens, line, pos, x) for x in range(0, l + 1)])
                            if candidate in self.lexicon:
                                continue
                            candidates.append((candidate, tpl))
                            cdc[candidate] += 1

        self.candidates = sorted(cdc.items(), key=lambda x: x[1], reverse=True)

        return candidates

    def extend_fuzzy(self) -> None:
        """
        Extend the lexicon with new fuzzy matches.
        """
        lexicon_entries = [' '.join(e) for e in self.lexicon.keys()]
        matches = get_fuzzy_matches(self.words, lexicon_entries)
        matches += get_fuzzy_matches_multi(self.records, self.lexicon, self.pmi)
        for match, entry, val in matches:
            new = tuple(match.split())
            if new not in self.lexicon:
                self.lexicon[new] = LexiconEntry(new, match, class_=Tag.FUZ, parent=tuple(entry.split()))

    def start_review(self, candidates=None, steps=20, n=250) -> None:
        """
        Start the GUI for a review session.
        Right mouse button marks a candidate as match (red), ambiguous (purple), or rejected (black, default).
        All non-marked (black) candidates are added to the rejects list.

        :param candidates: list of candidates to review
        :param steps: number of candidates to show at a time
        :param n: maximum number of candidates to review
        """
        if not candidates:
            candidates = self.candidates[:n]
        gui = ReviewGUI(candidates, self.rejected, steps=steps)
        self.rejected = gui.rejects
        self.candidates = self.candidates[n:]
        for mat, cls in gui.matches:
            self.lexicon[mat] = LexiconEntry(mat, ' '.join(mat), class_=cls)

    def save_lexicon(self, path=get_wd() + '/data/lexicon.pickle'):
        with open(path, 'wb') as file:
            pickle.dump(self.lexicon, file)

    def load_lexicon(self, path=get_wd() + '/data/lexicon.pickle'):
        with open(path, 'rb') as file:
            self.lexicon = pickle.load(file)

    def save_rejected(self, path=get_wd() + '/data/rejected.pickle'):
        with open(path, 'wb') as file:
            pickle.dump(self.rejected, file)

    def load_rejected(self, path=get_wd() + '/data/rejected.pickle'):
        with open(path, 'rb') as file:
            self.rejected = pickle.load(file)

    def save_pos_stats(self, path=get_wd() + '/data/pos_stats.pickle'):
        with open(path, 'wb') as file:
            pickle.dump((self.pos_counter, self.pos_counter_m), file)

    def load_pos_stats(self, path=get_wd() + '/data/pos_stats.pickle'):
        with open(path, 'rb') as file:
            self.pos_counter, self.pos_counter_m = pickle.load(file)

    def save_all(self):
        self.save_lexicon()
        self.save_pos_stats()
        self.save_rejected()

    def load_all(self):
        self.load_lexicon()
        self.load_pos_stats()
        self.load_rejected()
