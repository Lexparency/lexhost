from lxml import etree as et
from rdflib import Graph
import re
from collections import defaultdict
import logging
from copy import deepcopy

from .utils.generics import ignore_void_dict
from .utils.htm import undress, inner_tostring
from . import model as dm
from .toccordior import ContentsTable
from .history import DocumentVersion
from settings import DEFAULT_IRI


class DataIntegrityException(Exception):
    pass


def adapt_ids(element: et.ElementBase, id_prefix):
    for item in element.xpath('.//*[@id]'):
        id_ = item.attrib['id']
        if id_.startswith(id_prefix):
            item.attrib['id'] = id_.replace(id_prefix, '', 1)


class Twix(dm.Twix):
    MAXLEN = 10 ** 6

    def __init__(self, element: et.ElementBase):
        dressed = inner_tostring(element, skip_ns_declarations=True,
                                 simplify_blanks=True)
        stripped = undress(element)
        if len(stripped) > self.MAXLEN:
            stripped = stripped[:self.MAXLEN]
        super().__init__(dressed=dressed, stripped=stripped)


class Preamble(dm.Preamble):

    def __init__(self, element: et.ElementBase):
        meta_id = 'PRE'
        recitals = et.Element('recitals')
        adapt_ids(element, meta_id + '-')
        for recital in element.xpath('.//*[@class="lxp-recital"]'):
            # remove them from the preamble
            recitals.append(recital)
        super().__init__(
            recitals=[Recital(e)
                      for e in recitals.xpath('.//*[@class="lxp-recital"]')],
            body=Twix(element),
            ordinate=element.attrib['title'],
            meta={'_id': meta_id}
        )

    def toc_node(self) -> dm.ContentsTableNode:
        return dm.ContentsTableNode(
            locator=self.meta.id,
            heading=dm.Heading(ordinate=self.ordinate)
        )


class Heading(dm.Heading):
    def __init__(self, element: et.ElementBase):
        parts = {}
        for heading_part in ('ordinate', 'title'):
            part = element.find(f'./*[@class="lxp-{heading_part}"]')
            if part is not None:
                # TODO: actually, this step only involves an "inner_tostring".
                #  However, the toccordion would not be rendered correctly,
                #  with the current implementation, if the heading titles or
                #  ordinates contain html.
                parts[heading_part] = undress(part)
        super().__init__(**parts)


class Recital(dm.Recital):
    def __init__(self, element: et.ElementBase):
        body = Twix(element)
        title = element.attrib.get('title')
        if title:
            super().__init__(body=body, inferred_title=title)
        else:
            super().__init__(body=body)


class Definition(dm.Definition):
    def __init__(self, element: et.ElementBase):
        # TODO: clarify: Could definitions be nested? i.e. contain other
        #  definitions? If so, following query is problematic.
        terms = [
            et.tostring(e, method='text', with_tail=False, encoding='unicode')
            for e in element.xpath('.//*[@class="lxp-definition-term"]')
        ]
        super().__init__(
            terms=terms,
            body=Twix(element),
            meta={'_id': 'DEF_' + element.attrib['id'].replace('-', '_')}
        )


class Article(dm.Article):

    def __init__(self, element: et.ElementBase):
        adapt_ids(element, element.attrib['id'] + '-')
        super().__init__(
            heading=Heading(element.find('./*[@class="lxp-heading"]')),
            body=Twix(element.find('./*[@class="lxp-body"]')),
            meta={'_id': element.attrib['id']}
        )

    def toc_node(self):
        return dm.ContentsTableNode(
            locator=self.meta.id,
            heading=self.heading
        )


class ContentsTableNode(dm.ContentsTableNode):
    def __init__(self, element: et.ElementBase):
        # A little integrity check can't hurt
        children = element.xpath('./*[@class="lxp-container"] '
                                 '| ./*[@class="lxp-article"] ')
        heading = Heading(element.find('./*[@class="lxp-heading"]'))
        super().__init__(
            locator=element.attrib['id'],
            heading=heading,
            children=[sub.attrib['id'] for sub in children]
        )


class DocumentReceiver(DocumentVersion):

    _abstract_fields = dm.Abstract.get_fields()
    _cover_fields = dm.Cover.get_fields()

    @classmethod
    def relaxed_instantiation(cls, sauce: str,
                              logger=logging.getLogger(__name__)):
        source = et.fromstring(
            sauce,
            parser=et.HTMLParser(remove_blank_text=True, remove_comments=True))
        try:
            return cls(source, logger)
        except DataIntegrityException:
            logger.warning("Something went wrong", exc_info=True)
            body = source.find('body')
            source.remove(body)
            return cls(source, logger)

    def __init__(self, source: et.ElementBase, logger: logging.Logger):
        self.logger = logger
        self.source = source
        assert self.source.attrib['lang'].lower() == dm.language
        self.graph = LexGraph(self.source)
        date_document = self.graph.date_document
        cover = self._extract_cover()
        super().__init__(version=cover.abstract.version[0],
                         cover=cover,
                         date_document=date_document)
        self.available = False
        if self.source.find('body') is not None:
            self._adapt_references()
            self.definitions = [
                # Definitions come first. Otherwise extraction per article
                Definition(element)
                for element in self.source.xpath('.//*[@class="lxp-definition"]')
            ]
            self.preamble = Preamble(
                self.source.find('.//*[@class="lxp-preamble"]'))
            self.toc = dm.ContentsTable(table=[self.preamble.toc_node()])
            self.articles = []
            for element in self.source.xpath('//*[@class="lxp-article"] '
                                             '| //*[@class="lxp-final"]'
                                             '| //*[@class="lxp-container"]'):
                # Note that the order of self.toc.table matters!
                if element.attrib['class'] in ("lxp-article", "lxp-final"):
                    article = Article(element)
                    self.articles.append(article)
                    self.toc.table.append(article.toc_node())
                else:
                    self.toc.table.append(ContentsTableNode(element))
            self._insert_base()
            self.integrity_checks()  # Currently no check on metadata.
            self.available = True
        self._set_ids()

    def integrity_checks(self):
        """ Check if the submitted document would work as expected """
        try:
            toc = ContentsTable(table=deepcopy(self.toc.table))
            toc.toccordior(self.version)
        except Exception as e:
            raise DataIntegrityException(str(e))

    def _adapt_references(self):
        prefix = (f'/{self.cover.abstract.domain}'
                  f'/{self.cover.abstract.id_local}/')
        for article in self.source.xpath(
                '//article[@class!="lxp-mesa-article" and @id]'):
            id_ = article.attrib['id']
            mesa_ids = {i for i in article.xpath('.//@id')
                        if not i.startswith(f"{id_}-")}
            for anchor in article.xpath('.//a[@href]'):
                href = anchor.attrib['href']
                if href.startswith(f'#{id_}-'):
                    anchor.attrib['href'] = href.replace(f'#{id_}-', '#')
                elif href.startswith('#toc-'):
                    anchor.attrib['href'] = prefix + 'TOC' + href
                elif href.startswith('#') and not (href[1:] in mesa_ids):
                    if '-' in href:
                        tail = href[1:].replace('-', '/#', 1).strip('#')
                    else:
                        tail = href[1:] + '/'
                    anchor.attrib['href'] = prefix + tail

    def _extract_cover(self):
        cover = self.graph.plain_predicates()
        abstract = {key: cover.pop(key)[0]
                    for key in set(self._abstract_fields) & set(cover.keys())}
        for key in set(cover.keys()) - set(self._cover_fields):
            del cover[key]  # removing all unsupported fields
        for key, values in cover.items():
            # TODO: The "multi=True" fields should be determined
            #  via introspection
            if key not in ('passed_by', 'is_about'):
                cover[key] = values[0]
        abstract['version'] = [abstract['version']]
        missed = \
            set(self._abstract_fields) - set(abstract.keys()) - {'is_latest'}
        for miss in missed:
            self.logger.warning(f'Missing filter field: {miss}')
        cover['abstract'] = dm.Abstract(**abstract)
        for referral_type, anchors in self.graph.iter_anchors():
            cover[referral_type] = anchors
        return dm.Cover(**cover)

    def _insert_base(self):
        """ Inserts all fields that belong to dm.Base """
        self.cover.score_multiplier = int(1000 * self.importance_rule())
        # noinspection PyTypeChecker
        for es_doc in self.articles + self.definitions + [self.toc, self.preamble]:
            es_doc.abstract = self.cover.abstract
            es_doc.score_multiplier = self.cover.score_multiplier

    def _set_ids(self):
        id_prefix = (f"{self.cover.abstract.domain}-"
                     f"{self.cover.abstract.id_local}")
        type_2_inter = {
            dm.ContentsTable: 'TOC', Preamble: 'PRE', dm.Cover: 'COV'}
        for part in self.iter_parts():
            inter = type_2_inter.get(type(part))
            if type(part) in (Article, Definition):
                inter = part.meta.id
            part.meta.id = '-'.join((id_prefix, inter, self.version))

    def importance_rule(self):
        if getattr(self.cover, 'short_title', False):
            return 1.0
        # CRR has ca. 500 Articles as coarse reference
        return round(0.8 * min(500, len(self.articles)) / 500.0, 6)


class LexGraph(Graph):

    custom_namespace = {
        'eli': 'http://data.europa.eu/eli/ontology#',
        'lxp': 'http://lexparency.org/ontology#'
    }

    referral_types = list(dm.Cover.iter_anchors())

    relevant_prefixes = re.compile("^(?P<prefix>{})".format(
        '|'.join(custom_namespace.values())) + "(?P<predicate>.+)")

    def __init__(self, document: et.ElementBase):
        super().__init__()
        for pair in self.custom_namespace:
            self.bind(*pair)
        self.parse(
            data=et.tostring(document, encoding='unicode', method='xml'),
            # The actual ID is not known at the moment of parsing. And is not needed.
            publicID=DEFAULT_IRI,
            format='rdfa'
        )

    @property
    def date_document(self):
        result = self.query("""
            SELECT ?o
            WHERE {{
                <{this}> eli:date_document ?o .
                FILTER(isLiteral(?o))
            }}
        """.format(this=DEFAULT_IRI))
        for (o,) in result:
            return o.toPython()

    def plain_predicates(self) -> dict:
        result = self.query("""
            SELECT ?p ?o
            WHERE {{
                <{this}> ?p ?o .
                FILTER(isLiteral(?o))
            }}
        """.format(this=DEFAULT_IRI))
        outcome = defaultdict(list)
        for p, o in result:
            m = self.relevant_prefixes.match(p)
            if m is None:
                continue
            outcome[m.group('predicate')].append(o.toPython())
        return outcome

    def iter_anchors(self):

        def implemented(v, r_type):
            if v is None:
                if r_type in dm.Anchor.changers:
                    return False  # is the default for referrers
                return
            return v.toPython() == DEFAULT_IRI

        for referral_type in self.referral_types:
            query_result = self.query(f"""
                SELECT ?href ?title ?text ?v
                WHERE {{
                    <{DEFAULT_IRI}> eli:{referral_type} ?href .
                    ?href lxp:id_human ?text .
                    OPTIONAL {{
                        ?href eli:title ?title .
                    }}
                    OPTIONAL {{
                        ?v lxp:version_implements ?href .
                    }}
                }}
            """)
            if not query_result:
                continue
            yield referral_type, [
                dm.Anchor(**ignore_void_dict(
                    href=href.toPython(),
                    text=text.toPython() if text is not None else None,
                    title=title.toPython() if title is not None else None,
                    implemented=implemented(v, referral_type)
                ))
                for href, title, text, v in query_result
            ]
