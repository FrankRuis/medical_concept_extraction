from data_utils import get_wd, LexiconEntry
import pickle
from extraction import extract_all


def get_false_positives(records, lexicon, pos_counter=None, pos_counter_m=None, new_entry=None, mode='soft',
                        path=get_wd() + '/data/annotated.pickle'):
    """
    Finds all false positives for the given lexicon in the given annotated dataset.

    Soft mode ignores multi-token errors if part of the multi-token has been matches successfully, e.g.:
    Ground truth: mono cedocard
    Lexicon entry: mono cedocard retard
    Hard mode counts retard as false positive, soft mode does not.

    :param records: records to check
    :param lexicon: list of lexicon entries
    :param pos_counter: positional token counter for global contexts
    :param pos_counter_m: positional token counter for match contexts
    :param new_entry: new lexicon entry to check for false positives
    :param mode: soft or hard
    :param path: annotation file location
    :return: list of (false positive, record id, (line, position), context) tuples
    """
    with open(path, 'rb') as file:
        tags = pickle.load(file)

    lexicon = lexicon.copy()
    if new_entry:
        if isinstance(new_entry, list):
            for e in new_entry:
                if not isinstance(e, tuple):
                    e = tuple(e)
                lexicon[e] = LexiconEntry(e, ' '.join(e))
        else:
            if not isinstance(new_entry, tuple):
                new_entry = tuple(new_entry)
            lexicon[new_entry] = LexiconEntry(new_entry, ' '.join(new_entry))

    records = [r for r in records if r.id in tags]
    for r in records:
        r.tags = {}

    extract_all(records, lexicon, pos_counter=pos_counter, pos_counter_m=pos_counter_m)
    fps = []
    for record, tag in ((record, tags[record.id]) for record in records if record.id in tags):
        for (l, p) in record.tags:
            if record.tokens[l][p]:
                if (l, p) not in tag:
                    if mode == 'soft':
                        if p - 1 >= 0 and (l, p - 1) in tag:
                            continue
                    fps.append((record.tokens[l][p], record.id, (l, p), record.tokens[l][p-3:p+4]))

    return fps


def get_tags(path=get_wd() + '/data/annotated.pickle'):
    with open(path, 'rb') as file:
        return pickle.load(file)


def save_tags(tags, path=get_wd() + '/data/annotated.pickle'):
    with open(path, 'wb') as file:
        pickle.dump(tags, file)


def remove_tag(tags, id, pos, save=True):
    del tags[id][pos]
    if save:
        save_tags(tags)


def add_tag(tags, id, pos, save=True):
    tags[id][pos] = True
    if save:
        save_tags(tags)
