import tkinter as tk
from tkinter import font
from data_utils import Tag, get_wd
from random import choice
import pickle


class AnnotationGUI:
    def __init__(self, records, filter_=None):
        """
        GUI for annotating records.

        :param records: list of records to annotate
        :param filter_: optional list of record ids to ignore (e.g. if they have already been annotated)
        """
        self.records = [r for r in records.copy() if r.id not in filter_] if filter_ else records.copy()
        self.cur = None
        self.ttt = {}
        self.annotated = {}

        self.root = tk.Tk()
        custom_font = font.Font(family='Raavi', size=12)
        self.top = tk.Frame(self.root)
        self.top.pack(side=tk.TOP)

        self.text = tk.Text(self.root, font=custom_font, width=80, height=40)
        self.text.pack(in_=self.top, side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.bottom = tk.Frame(self.root)
        self.bottom.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        self.text.tag_config('mat', foreground='red')
        self.text.tag_bind('mat', "<Button-3>", self._callback)
        self.text.tag_config('reg', foreground='black')
        self.text.tag_bind('reg', "<Button-3>", self._callback)

        self.next_button = tk.Button(self.root, text="Next", command=self._next_record)
        self.next_button.pack(in_=self.bottom, side=tk.LEFT)

        self.save_button = tk.Button(self.root, text="Save", command=self._save_record)
        self.save_button.pack(in_=self.bottom, side=tk.RIGHT)
        self._next_record()

        self.root.mainloop()

    def _next_record(self, event=None):
        self.text.delete('1.0', tk.END)
        if len(self.records) == 0:
            return
        self.cur = choice(self.records)
        self.records.remove(self.cur)
        self.ttt.clear()
        for ln, line in enumerate(self.cur.tokens):
            for i, w in enumerate(line):
                cid = self.text.index(tk.INSERT)
                if (ln, i) in self.cur.tags:
                    self.text.insert(tk.END, w, 'mat')
                else:
                    self.text.insert(tk.END, w, 'reg')
                self.ttt[(cid, self.text.index(tk.INSERT))] = (ln, i)
                self.text.insert(tk.END, ' ')
            self.text.insert(tk.END, '\n')

    def _save_record(self, path=get_wd() + '/data/annotated.pickle'):
        if self.cur.id not in self.annotated:
            self.annotated[self.cur.id] = self.cur.tags

        with open(path, 'wb') as file:
            pickle.dump(self.annotated, file)

    def _callback(self, event):
        index = event.widget.index("@%s,%s" % (event.x, event.y))

        tag_indices = list(event.widget.tag_ranges('mat'))
        reg_indices = list(event.widget.tag_ranges('reg'))

        for start, end in zip(tag_indices[0::2], tag_indices[1::2]):
            if event.widget.compare(start, '<=', index) and event.widget.compare(index, '<', end):
                self.text.tag_remove('mat', start, end)
                self.text.tag_add('reg', start, end)
                del self.cur.tags[self.ttt[(str(start), str(end))]]

        for start, end in zip(reg_indices[0::2], reg_indices[1::2]):
            if event.widget.compare(start, '<=', index) and event.widget.compare(index, '<', end):
                self.text.tag_remove('reg', start, end)
                self.text.tag_add('mat', start, end)
                self.cur.tags[self.ttt[(str(start), str(end))]] = True


class ReviewGUI:
    def __init__(self, candidates, rejects=None, steps=20):
        """
        Starts the GUI.

        :param candidates: ordered list of candidates to review
        :param rejects: set of rejected candidates from earlier runs
        :param steps: number of candidates on screen at once
        """
        self.matches = set()
        if not rejects:
            rejects = set()

        self._rejects = rejects
        self.candidates = candidates

        self.root = tk.Tk()
        custom_font = font.Font(family='Raavi', size=12)
        self.top = tk.Frame(self.root)
        self.top.pack(side=tk.TOP)

        self.text = tk.Text(self.root, font=custom_font, width=80, height=10)
        self.text.pack(in_=self.top, side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.text.tag_config('amb', foreground='purple')
        self.text.tag_bind('amb', "<Button-3>", self._callback)
        self.text.tag_config('mat', foreground='red')
        self.text.tag_bind('mat', "<Button-3>", self._callback)
        self.text.tag_config('reg', foreground='black')
        self.text.tag_bind('reg', "<Button-3>", self._callback)

        self.cur = 0
        self.steps = steps
        self._next_candidates()

        self.bottom = tk.Frame(self.root)
        self.bottom.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        button = tk.Button(self.root, text="Next", command=self._next_candidates)
        button.pack(in_=self.bottom, side=tk.LEFT)

        self.root.mainloop()

    @property
    def rejects(self):
        """
        Reject all unmarked candidates seen so far.
        :return: set containing rejected candidates
        """
        return self._rejects.union(set(self.candidates[:self.cur]) - {m[0] for m in self.matches})

    def _callback(self, event):
        """
        Handle right mouse click on a candidate.

        :param event: click event
        """
        index = event.widget.index("@%s,%s" % (event.x, event.y))

        amb_indices = list(event.widget.tag_ranges('amb'))
        tag_indices = list(event.widget.tag_ranges('mat'))
        reg_indices = list(event.widget.tag_ranges('reg'))

        # change tag from match to ambiguous
        for start, end in zip(tag_indices[0::2], tag_indices[1::2]):
            if event.widget.compare(start, '<=', index) and event.widget.compare(index, '<', end):
                self.text.tag_remove('mat', start, end)
                self.text.tag_add('amb', start, end)
                spl = self.text.get(start, end).split()
                m = tuple(spl)
                self.matches.remove((m, Tag.REG))
                self.matches.add((m, Tag.AMB))

        # change tag from ambiguous to rejected
        for start, end in zip(amb_indices[0::2], amb_indices[1::2]):
            if event.widget.compare(start, '<=', index) and event.widget.compare(index, '<', end):
                self.text.tag_remove('amb', start, end)
                self.text.tag_add('reg', start, end)
                spl = self.text.get(start, end).split()
                m = tuple(spl)
                self.matches.remove((m, Tag.AMB))

        # change tag from rejected to match
        for start, end in zip(reg_indices[0::2], reg_indices[1::2]):
            if event.widget.compare(start, '<=', index) and event.widget.compare(index, '<', end):
                self.text.tag_remove('reg', start, end)
                self.text.tag_add('mat', start, end)
                spl = self.text.get(start, end).split()
                m = tuple(spl)
                self.matches.add((m, Tag.REG))

    def _next_candidates(self, event=None):
        """
        Load the next

        :param event: button click event
        """
        self.text.delete('1.0', tk.END)
        for i in range(self.cur, self.cur + self.steps):
            if len(self.candidates) > i:
                self.text.index(tk.INSERT)
                self.text.insert(tk.END, self.candidates[i], 'reg')
                self.text.insert(tk.END, ', ')
                self.cur += 1
            else:
                break


if __name__ == '__main__':
    gui = ReviewGUI([('test', str(i)) for i in range(35)], set())
