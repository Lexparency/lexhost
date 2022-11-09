import os
import re
from collections import namedtuple
from datetime import date
from functools import lru_cache
from typing import Match, List
from operator import attrgetter

import lexref
from elasticsearch import NotFoundError
from lexref.celex_handling import celexer

from legislative_act.model import Cover
from legislative_act.provider import DocumentProvider
from legislative_act.searcher import display_dictionary
from settings import LANG_2
from views.exceptions import convert_exception

LANG = LANG_2.upper()


class TitledLocation(namedtuple("TL", ["href", "title"])):
    @property
    def depth(self):
        """1: Document level;  >1: Below document level"""
        return self.href.strip("/").count("/")

    @property
    @lru_cache()
    def path(self):
        return self.href.strip("/").split("#")[0].split("/")

    @property
    def domain(self):
        return self.path[0]

    @property
    def id_local(self):
        return self.path[1]

    @property
    def fragment_id(self):
        try:
            return self.path[2]
        except IndexError:
            return

    @property
    def snippet(self):
        try:
            return self.href.strip("/").split("#")[1]
        except IndexError:
            return 0

    def get_cover_display_dictionary(self):
        return display_dictionary(
            Cover.get(f"{self.domain}-{self.id_local}-COV-initial")
        )

    @convert_exception(Exception, NotFoundError)
    def get_display_dictionary(self):
        if self.depth == 1:  # hit on document level
            return self.get_cover_display_dictionary()
        try:
            dp = DocumentProvider(self.domain, self.id_local)
            return {
                "id_human": self.title or self.fragment_id or self.href,
                "title": None,
                "highlights": dp.get_snippet(
                    self.fragment_id, dp.latest_available, self.snippet
                ),
                "href": self.href,
            }
        except NotFoundError:
            return self.get_cover_display_dictionary()


class NumberYear(namedtuple("NY", ["number", "year"])):
    year_range = (1944, date.today().year)

    @classmethod
    def create(cls, intable):
        n = int(intable)
        return cls(str(n).zfill(4), cls.as_year(n))

    @classmethod
    def as_year(cls, n):
        if cls.year_range[0] <= n <= cls.year_range[1]:
            return str(n)
        if 44 <= n <= 99:
            return str(1900 + n)


class DeadSimpleShortCut:

    numbers = re.compile(r"\b(?P<n1>[0-9]{1,4})[^0-9]+(?P<n2>[0-9]{1,4})\b")
    inters = "FRLD"
    annex_ordinate = re.compile(r"\b([ivx]{1,5})\b", flags=re.I)
    article_ordinate = re.compile(r"\b([1-9][0-9]*[a-z]{0,2})\b", flags=re.I)

    def __init__(self, search_words, context=("eu",)):
        self.search_words = search_words.strip()
        self.context = context

    @classmethod
    def match_2_id_local(cls, m: Match) -> List[str]:
        numbers = [NumberYear.create(m.group(n)) for n in ("n1", "n2")]
        for inter in cls.inters:
            path = f"3{{y}}{inter}{{n}}".format
            for b in (0, 1):
                if numbers[b].year is None:
                    continue
                yield path(y=numbers[b].year, n=numbers[1 - b].number)

    @property
    def paths(self):
        if len(self.context) == 1:
            for match in self.numbers.finditer(self.search_words):
                for id_local in self.match_2_id_local(match):
                    yield "/" + "/".join(self.context + (id_local,)) + "/"
        if len(self.context) == 2:  # i.e. document-context
            for leaf_type, pattern, std in [
                ("ART", self.article_ordinate, str.lower),
                ("ANX", self.annex_ordinate, str.upper),
            ]:
                match = pattern.match(self.search_words)
                if match is None:
                    continue
                ordinate = std(match.group())
                fragment_id = f"{leaf_type}_{ordinate}"
                yield "/" + "/".join(self.context + (fragment_id,)) + "/"

    @property
    def locations(self):
        return sorted(
            {TitledLocation(path, None) for path in self.paths},
            reverse=True,
            key=attrgetter("href"),
        )


def get_abbreviations():
    file_path = os.path.join(
        os.path.dirname(lexref.__file__), "static", "named_entity.csv"
    )
    with open(file_path, encoding="utf-8") as f:
        lines = [line.strip().split(",") for line in f.readlines()]
    assert lines[0] == ["tag", "language", "title_pattern", "abbreviation", "title"]
    return [line[3] for line in lines if line[1].upper() == LANG and line[3] != ""]


class ShortCutter:
    """
    Provides a search short-cut, if the search-term actually contains a reference.
    TODO: Implement respect for the filter options!
    """

    upper_2_normal = {a.upper(): a for a in get_abbreviations()}
    abbrev_pattern = re.compile(
        r"\b({})\b".format("|".join(upper_2_normal.values())), flags=re.I
    )

    def __init__(self, search_words, document_context=None):
        """Wrapper around the Reflector class from the lexref package
        :param search_words: E.g. CRR Article 16 Paragraph 3
        :param document_context: E.g. /eu/32013R0575
        """
        self.search_words = search_words
        self.document = document_context
        self.r = lexref.Reflector(
            LANG,
            "annotate",
            min_role="document" if document_context is None else None,
            document_context=document_context,
            internet_domain="",
        )
        self.title_split = None
        if document_context is not None:
            domain, id_local = document_context.strip("/").split("/")[:2]
            if domain == "eu":
                # noinspection PyBroadException
                try:
                    self.title_split = celexer.invert(id_local, LANG)[1]
                except Exception:
                    pass

    @property
    def context(self):
        if self.document is None:
            return ("eu",)
        return tuple(self.document.strip("/").split("/"))

    @property
    def preprocessed_search_words(self):
        """Since abbreviation patterns in the lexref package are
        not case-sensitive, the upper-cased versions need to be further
        processed.
        """
        sw = self.search_words
        for key in self.abbrev_pattern.findall(self.search_words):
            sw = re.sub(rf"\b{key}\b", self.upper_2_normal[key.upper()], sw)
        return sw

    @property
    @lru_cache()
    def reference(self):
        result = set()
        for refs in self.r(self.preprocessed_search_words):
            for ref in refs["references"]:
                title = ref["title"]
                if self.title_split is not None:
                    # e.g. /eu/32012R0923/search?search_words=SERA.5005+Buchstabe+f
                    try:
                        title = title.split(self.title_split)[1]
                    except IndexError:
                        pass
                result.add(TitledLocation(ref["href"], title))
        try:
            return sorted(result, reverse=True, key=attrgetter("href"))[0]
        except IndexError:
            return

    @classmethod
    def hits_from(cls, *args, **kwargs):
        # noinspection PyBroadException
        try:
            self = cls(*args, **kwargs)
            return self.hits
        except Exception:
            return []

    @property
    def hits(self):
        references = DeadSimpleShortCut(self.search_words, self.context).locations
        if self.reference is not None:
            if not (self.reference.depth == 1 and self.document is not None):
                references = [self.reference]
        if not references:
            return []
        if references[0].depth == 1 and self.document is not None:
            return []
        result = []
        for ref in references:
            result.append(ref.get_display_dictionary())
        return result
