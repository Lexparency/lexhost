from copy import deepcopy
from datetime import date
from functools import lru_cache, reduce
import re
from html import escape

from django.template import loader
from lxml import etree as et
from elasticsearch.exceptions import NotFoundError

from lexhost.settings import LANG_2
from lexhost.apps.exceptions import convert_exception

from .toccordior import ContentsTable
from . import model as doc
from .history import DocumentHistory
from .searcher import DocumentSearcher
from .utils import human_date
from .utils.generics import Clearable
from .receiver import Twix


MAXSIZE = 1024

naive_ints = re.compile(r'\b[0-9]+[a-z]{,2}\b')
naive_roms = re.compile(r'\b[IVX]{1,4}\b', flags=re.I)


class Preamble(doc.Preamble):

    def render_preamble_body(self) -> et.ElementBase:
        """ This is just an intermediate solution, in order to use the same
            template for preambles as is used for articles.
        """
        remainder = et.fromstring(
            "<article>{}</article>".format(self.body.dressed),
            parser=et.XMLParser())
        recital_container = remainder.find('.//ol[@class="lxp-recitals"]')
        for k, recital in enumerate(self.recitals):
            recital_container.append(et.fromstring(
                "<li data-title=\"({label})\">{content}</li>".format(
                    label=str(k + 1),
                    content=recital.body.dressed
                ),
                parser=et.XMLParser()
            ))
        return remainder


class DocumentProvider(Clearable):

    def __init__(self, domain, did):
        self.domain = domain
        self.id_local = did
        self.history = DocumentHistory.get(f'{self.domain}-{self.id_local}')
        self.title = doc.Cover.get(f'{domain}-{did}-COV-{self.first_version}').title

    @property
    @lru_cache()
    def base_id(self):
        return f"{self.domain}-{self.id_local}"

    def version_hidden_version(self, version: str):
        hidden_version = version
        if version == 'latest':
            hidden_version = self.latest_available
            if not self.current_is_available:
                version = hidden_version
        return version, hidden_version

    @property
    @lru_cache(maxsize=MAXSIZE)
    def latest_available(self):
        return self.history.latest_available

    @property
    @lru_cache(maxsize=MAXSIZE)
    def first_version(self):
        for availability in self.history.availabilities:
            return availability.version

    @property
    @lru_cache(maxsize=MAXSIZE)
    def current(self):
        return self.history.latest

    def is_future_version(self, version):
        if version == 'latest':
            return False
        for availability in self.history.availabilities:
            if availability.version == version:
                if availability.date_document > date.today():
                    return True

    @property
    @lru_cache(maxsize=MAXSIZE)
    def current_is_available(self):
        return self.current == self.latest_available

    @property
    @lru_cache(maxsize=MAXSIZE)
    def versions_map(self):
        return self.history.exposed_to_hidden

    @lru_cache(maxsize=MAXSIZE)
    def get_versions_availability(self, sub_id):
        if sub_id == 'TOC':
            versions = [v.version for v in self.history.availabilities]
        else:
            versions = self.get_leaf_versions(sub_id)
        result = [
            {
                'display': human_date(availability.date_document, LANG_2),
                'date_document': availability.date_document,
                'loaded': availability.available,
                'folder': availability.version,
                'id': availability.version  # will not be overridden.
            }
            for availability in self.history.availabilities
            if availability.version in versions
        ]
        for item in reversed(result):
            if item['date_document'] <= date.today() and item['loaded']:
                item['folder'] = ''
                break
        return result

    @lru_cache(maxsize=MAXSIZE)
    def toc(self, version):
        return ContentsTable.get(self.get_part_id('TOC', version))

    @lru_cache(maxsize=MAXSIZE)
    def get_toccordion(self, hidden_version, version, document_id=None):
        document_id = document_id or self.id_local
        return et.tostring(
            self.toc(hidden_version).toccordior(version, document_id),
            encoding='unicode')

    @lru_cache(maxsize=MAXSIZE)
    def get_cover(self, version) -> doc.Cover:
        return doc.Cover.get(self.get_part_id('COV', version))

    @lru_cache(maxsize=MAXSIZE)
    def render_article_body(self, fragment_id, version):
        article = self.get_article(fragment_id, version)
        if article.heading.title is None:
            return et.fromstring(
                "<article>{}</article>".format(article.body.dressed),
                parser=et.XMLParser())
        return et.fromstring(
            "<article title=\"{}\">{}</article>".format(
                escape(article.heading.title), article.body.dressed),
            parser=et.XMLParser()
        )

    @property
    def basic_error_msg(self):
        return f'Could not find fragment {repr(self.domain)}' \
               f', {repr(self.id_local)}.'

    def get_leaf_versions(self, sub_id):
        try:
            return reduce(lambda a, b: list(a) + list(b),
                          self.history.hidden_to_exposed[sub_id].values(), [])
        except IndexError:
            raise NotFoundError(', '.join((self.basic_error_msg, repr(sub_id))))

    def get_part_id(self, sub_id, version):
        try:
            return '-'.join(
                (self.base_id, sub_id, self.versions_map[(sub_id, version)]))
        except KeyError:
            raise NotFoundError(
                ', '.join((self.basic_error_msg, repr(sub_id), repr(version))))

    @lru_cache(maxsize=MAXSIZE)
    def get_article(self, sub_id, version) -> doc.Article:
        id_ = self.get_part_id(sub_id, version)
        if sub_id == 'PRE':
            # convert preamble to normal article
            preamble = Preamble.get(id_)
            return doc.Article(
                heading=doc.Heading(ordinate=preamble.ordinate),
                body=Twix(preamble.render_preamble_body()),
                abstract=preamble.abstract
            )
        return doc.Article.get(id_)

    @convert_exception(KeyError, NotFoundError)
    def get_snippet(self, fragment_id, version, snippet):

        def article_snippet():
            try:
                et.SubElement(out_element, 'b').text = article.attrib['title']
            except KeyError:
                pass
            try:
                innr = deepcopy(article.xpath('(.//*[self::li or self::p])[1]')[0])
            except IndexError:
                # occurs in lexparency.org/eu/32009R1223/ANX_VII/?snippet=0
                innr = deepcopy(article.xpath('(./*)[1]')[0])
            out_element.append(innr)
            out_element[-1].tag = 'p'
            et.SubElement(out_element, 'p').text = '...'
        out_element = et.Element('div')
        if fragment_id in ('PRE', 'TOC') and snippet == '0':
            inner = et.fromstring(f'<b>{self.title}</b>')
            out_element.append(inner)
            return et.tostring(out_element, encoding='unicode')
        if fragment_id == 'TOC':
            p = snippet.split('-')
            ids = ['-'.join(p[:k+1]) for k in range(1, len(p))]
            l2n = self.toc(version).locator_to_node()
            nodes = [l2n[id_]['heading'] for id_ in ids]
            return loader.render_to_string('fragments/toc_snippet.html',
                                           {'nodes': nodes, 'title': self.title})
        article = self.render_article_body(fragment_id, version)
        if snippet == '0':
            article_snippet()
        else:
            try:
                out_element.append(deepcopy(article.xpath(
                    f'(.//li[@id="{snippet}"])[1]')[0]))
            except IndexError:
                article_snippet()
            else:
                out_element[-1].tag = 'p'
        return et.tostring(out_element, encoding='unicode')

    def search(self, words, *, page=1, all_versions=False):
        searcher = DocumentSearcher(words, self.domain, self.id_local,
                                    all_versions=all_versions)
        return searcher.get_page(page)

    @classmethod
    @lru_cache(maxsize=MAXSIZE)
    def get(cls, domain, did):
        return cls(domain, did)
