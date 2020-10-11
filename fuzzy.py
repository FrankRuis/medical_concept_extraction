from sklearn.feature_extraction.text import TfidfVectorizer
from sparse_dot_topn import awesome_cossim_topn
from collections import Counter
import numpy as np


def get_fuzzy_matches(words, targets, n=2, lower_bound=0.85):
    """
    Fuzzy matching of single-token lexicon entries using TF-IDF matrices of character-level n-grams.

    :param words: list of tokens to find fuzzy matches in
    :param targets: list of targets to match to
    :param n: number of characters in the n-grams
    :param lower_bound: lower bound for cosine similarity
    :return: list of (fuzzy match, matched target, cosine similarity) tuples
    """
    vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(n, n), use_idf=False)
    vectorizer.fit(words + targets)
    tf_idf_words = vectorizer.transform(words)
    tf_idf_lexicon = vectorizer.transform(targets).transpose()
    matches = awesome_cossim_topn(tf_idf_words, tf_idf_lexicon, ntop=1, lower_bound=lower_bound).tocoo()

    return [(words[row], targets[col], val) for row, col, val in zip(matches.row, matches.col, matches.data)]


def calculate_pmi(records):
    """
    Calculate the pointwise mutual information for all 2-grams in the given records.

    :param records: list of records
    :return: {word_left: {word_right: pmi}} dictionary
    """
    sentences = [sentence for record in records for sentence in record.tokens if sentence]
    co_occurrence = {}
    counter = Counter({'<end>': len(sentences)})
    total = 0
    for sentence in sentences:
        for word in sentence:
            counter[word] += 1

    for sentence in sentences:
        sentence = [w for w in sentence if counter[w] > 1]
        total += len(sentence)
        for w1, w2 in [sentence[i:i + 2] if len(sentence[i:i + 2]) > 1 else [sentence[-1], '<end>'] for i in
                       range(len(sentence))]:
            if w1 in co_occurrence:
                co_occurrence[w1][w2] += 1
            else:
                co_occurrence[w1] = Counter({w2: 1})
    PMI = {}
    for w1 in co_occurrence:
        for w2 in co_occurrence[w1]:
            pab = co_occurrence[w1][w2] / total
            pa = sum(co_occurrence[w1].values()) / total
            pb = (sum(co_occurrence[w2].values()) if w2 != '<end>' else len(sentences)) / total
            pmi = np.log(pab / (pa * pb))
            if w1 in PMI:
                PMI[w1][w2] = pmi
            else:
                PMI[w1] = {w2: pmi}

    return PMI


def get_fuzzy_matches_multi(records, lexicon, pmi, n=2, pmi_bound=7, lower_bound=0.85):
    """
    Get fuzzy matches with a length of 2 and 3 tokens.

    :param records: list of records
    :param lexicon: lexicon to match to
    :param pmi: pointwise mutual information dict, as returned by calculate_pmi
    :param n: number of characters in the n-grams
    :param pmi_bound: pointwise mutual information threshold
    :param lower_bound: cosine similarity threshold
    :return: list of (fuzzy match, matched target, cosine similarity) tuples
    """
    double_tokens = {}
    for record in records:
        double_tokens[record.id] = []
        for sentence in record.tokens:
            for i, token in enumerate(sentence):
                if token in pmi and (i + 1) < len(sentence) and sentence[i + 1] in pmi[token]:
                    if pmi[token][sentence[i + 1]] > pmi_bound:
                        double_tokens[record.id].append((token + ' ' + sentence[i + 1], (i, i + 1)))

    triple_tokens = {}
    for record in records:
        triple_tokens[record.id] = []
        for i, double in enumerate(double_tokens[record.id]):
            if (i + 1) < len(double_tokens[record.id]) and double[1][1] == double_tokens[record.id][i + 1][1][0]:
                triple_tokens[record.id].append(double[0] + ' ' + double_tokens[record.id][i + 1][0].split()[1])

    words = list({t[0] for r in records for t in double_tokens[r.id]})
    lexicon_entries = [' '.join(e) for e in lexicon.keys() if len(e) > 1]
    matches = get_fuzzy_matches(words, lexicon_entries, n=n, lower_bound=lower_bound)

    words = list({t for r in records for t in triple_tokens[r.id]})
    for word, entry, val in get_fuzzy_matches(words, lexicon_entries):
        for w, e, v in matches:
            if w in word and v >= val:
                break
        else:
            matches.append((word, entry, val))

    return matches
