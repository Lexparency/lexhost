from lxml import etree as et
from collections import namedtuple
from datetime import date
from operator import attrgetter
import logging

from legislative_act import model as dm
from legislative_act.history import DocumentHistory
from settings import INTERNET_DOMAIN, DEBUG, FEATURED
from views.land import get_featured
from views.read import Diamonds

PROTOCOL = 'https'


class SitePlace(namedtuple('SitePlace',
                           ['loc', 'lastmod', 'changefreq', 'priority'])):

    def to_xml(self):
        url = et.Element('url')
        et.SubElement(url, 'loc').text = self.loc
        et.SubElement(url, 'lastmod').text = self.lastmod.strftime('%Y-%m-%d')
        et.SubElement(url, 'changefreq').text = self.changefreq
        et.SubElement(url, 'priority').text = str(self.priority)
        return url


class SiteMap(list):

    BIRTH_DATE = date(2020, 1, 1)

    def __init__(self, domain):
        super().__init__()
        self.domain = domain
        self.diamonds = Diamonds()
        self.append(SitePlace(  # landing page
            loc='{}://{}/'.format(PROTOCOL, INTERNET_DOMAIN),
            lastmod=date.today(),
            changefreq='monthly',
            priority=1.0
        ))
        self.logger = logging.getLogger()

    def to_xml(self, max_size=1000):
        max_size = min(max_size, len(self))
        sitemap = et.Element(
            'urlset', {'xmlns': "http://www.sitemaps.org/schemas/sitemap/0.9"})
        self.sort(key=attrgetter('priority'), reverse=True)
        for e in self[:max_size]:
            sitemap.append(e.to_xml())
        return sitemap

    def append(self, o):
        assert type(o) is SitePlace
        super().append(o)

    @staticmethod
    def get_changefreq(dh: DocumentHistory):
        if len(dh.availabilities) == 1:
            return 'yearly'
        diff = dh.availabilities[-1].date_document - dh.availabilities[-2].date_document
        if diff.days > 365:
            return 'yearly'
        return 'monthly'

    def get_site_place(self, id_local) -> SitePlace:
        dh = DocumentHistory.get(f'{self.domain}-{id_local}').datify()
        cover = dm.Cover.get(f'{self.domain}-{id_local}-COV-{dh.latest}')
        document_id = self.diamonds.get_alias(id_local)
        url_path = f'/{self.domain}/{document_id}/'
        return SitePlace(
            loc=f'{PROTOCOL}://{INTERNET_DOMAIN}{url_path}',
            lastmod=max(dh.availabilities[-1].date_document, self.BIRTH_DATE),
            changefreq=self.get_changefreq(dh),
            priority=cover.score_multiplier / 1000.)

    @classmethod
    def build(cls, domain):
        self = cls(domain)
        for item in get_featured(self.domain, FEATURED[self.domain]):
            id_local = item["id_local"]
            # noinspection PyBroadException
            try:
                self.append(self.get_site_place(id_local))
            except Exception:
                self.logger.error(f'Something went wrong for {id_local}',
                                  exc_info=True)
        return self

    def dump(self) -> bytes:
        return et.tostring(
            self.to_xml(),
            pretty_print=DEBUG,  # only for testing and development.
            method='xml',
            xml_declaration=True
        )


if __name__ == '__main__':
    print(SiteMap.build('eu').dump().decode('ascii'))
