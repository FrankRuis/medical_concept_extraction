from data_utils import Tag
from context_utils import get_at_n


def extract_all(records, lexicon, pos_counter=None, pos_counter_m=None, mxn=3, window=3):
    """
    Extract all matches from the given records using the given lexicon, saved in the records' tag objects.

    :param records: list of record objects
    :param lexicon: dictionary of lexicon items
    :param pos_counter: positional token counter for global contexts
    :param pos_counter_m: positional token counter for match contexts
    :param mxn: maximum number of tokens in a single lexicon entry
    :param window: context window size
    """
    for record in records:
        for ln, line in enumerate(record.tokens):
            for i, w in enumerate(line):
                for n in range(mxn - 1, -1, -1):
                    if (i + n) < len(line) and tuple(line[i + m] for m in range(n + 1)) in lexicon:
                        toks = tuple(line[i + m] for m in range(n + 1))
                        if lexicon[tuple(line[i + m] for m in range(n + 1))].class_ == Tag.AMB:
                            tpl = tuple([get_at_n(record.tokens, ln, i if k < 0 else i + n, k, lexicon) for k in
                                         range(-window, window + 1) if k != 0])
                            # ignore this entry if no positional counters provided
                            if not pos_counter or not pos_counter_m or _score_context(pos_counter, pos_counter_m,
                                                                                      tpl) < 0.01:
                                continue
                        for m in range(n + 1):
                            record.tags[(ln, i + m)] = Tag(ln, i + m, line[i + m], lexicon[toks].class_)


def _score_context(pos_counter_m, pos_counter, context) -> float:
    """
    Calculates the partial match score as described in the paper.

    :param context: context to calculate the score for
    :return: partial match score
    """
    cur = 0
    for i, e in enumerate(context):
        cur += pos_counter_m[(i, e)] / pos_counter[(i, e)]

    return cur / 6
