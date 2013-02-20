# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from itertools import chain
from collections import Counter, namedtuple
from ._utils import null_stemmer
from ..document import Document
from .._py3k import to_unicode


SentenceInfo = namedtuple("SentenceInfo", ("sentence", "order", "rating",))


class LuhnMethod(object):
    max_gap_size = 4
    significant_percentage = 1

    def __init__(self, document, stopwords=(), stemmer=null_stemmer):
        self._document = document
        self._stopwords = frozenset(stopwords)
        self._stemmer = stemmer

    def __call__(self, sentences_count):
        words = self._get_significant_words(self._document.words)

        sentences = []
        for order, sentence in enumerate(self._document.sentences):
            rating = self.rate_sentence(sentence, words)
            sentences.append(SentenceInfo(sentence, order, rating))

        # sort sentences by rating in descending order
        sorted_sentences = sorted(sentences, key=lambda s: -s.rating)
        # get first best rated `sentences_count` sentences
        sorted_sentences = sorted_sentences[:sentences_count]
        # sort sentences by their order in document
        ordered_sentences = sorted(sorted_sentences, key=lambda s: s.order)

        return tuple(i.sentence for i in ordered_sentences)

    def _get_significant_words(self, words):
        words = filter(self._is_stopword, words)
        words = tuple(self._stem_word(w) for w in words)

        # sort word by number of occurrences
        words = sorted((c, w) for w, c in Counter(words).items())

        # take only best `significant_percentage` % words
        best_words_count = int(len(words) * self.significant_percentage)
        return tuple(w for _, w in words)[:best_words_count]

    def _is_stopword(self, word):
        return not word.is_stopword(self._stopwords)

    def _stem_word(self, word):
        return self._stemmer(to_unicode(word).lower())

    def rate_sentence(self, sentence, significant_stems):
        ratings = self._get_chunk_ratings(sentence, significant_stems)
        return max(ratings) if ratings else 0

    def _get_chunk_ratings(self, sentence, significant_stems):
        chunks = []
        NONSIGNIFICANT_CHUNK = [0]*self.max_gap_size

        in_chunk = False
        for order, word in enumerate(sentence.words):
            stem = self._stem_word(word)
            # new chunk
            if stem in significant_stems and not in_chunk:
                in_chunk = True
                chunks.append([1])
            # append word to chunk
            elif in_chunk:
                is_significant_word = int(stem in significant_stems)
                chunks[-1].append(is_significant_word)

            # end of chunk
            if chunks and chunks[-1][-self.max_gap_size:] == NONSIGNIFICANT_CHUNK:
                in_chunk = False

        return tuple(map(self._get_chunk_rating, chunks))

    def _get_chunk_rating(self, chunk):
        chunk = self.__remove_trailing_zeros(chunk)
        words_count = len(chunk)
        assert words_count > 0

        significant_words = sum(chunk)
        if significant_words == 1:
            return 0
        else:
            return significant_words**2 / words_count

    def __remove_trailing_zeros(self, collection):
        collection = list(collection)
        while collection[-1] == 0:
            collection.pop()

        return collection
