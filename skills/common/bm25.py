"""Okapi BM25 implemented here (stdlib only; no third-party ranking dependency). Deterministic: ties broken by document order."""
import math
from collections import Counter

from skills.common.text import tokens


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.toks = [tokens(d) for d in docs]
        self.n = len(docs)
        self.avg = (sum(len(t) for t in self.toks) / self.n) if self.n else 0.0
        df = Counter()
        for t in self.toks:
            df.update(set(t))
        self.idf = {w: math.log(1 + (self.n - c + 0.5) / (c + 0.5)) for w, c in df.items()}
        self.tf = [Counter(t) for t in self.toks]

    def score(self, query, i):
        s, dl = 0.0, len(self.toks[i])
        for w in set(tokens(query)):
            f = self.tf[i].get(w, 0)
            if f:
                s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / (self.avg or 1)))
        return s

    def rank(self, query):
        """[(index, score)] best first; stable for equal scores."""
        return sorted(((i, self.score(query, i)) for i in range(self.n)), key=lambda x: (-round(x[1], 9), x[0]))
