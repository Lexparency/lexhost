import re
from time import sleep

from legislative_act import model as dm
from settings import LANG_2

LANG_2 = LANG_2.upper()

BURL = f'https://eur-lex.europa.eu/legal-content/{LANG_2}/ALL/?uri=CELEX:'

CCLXPTN = re.compile(
    BURL.replace('?', r'\?') + '0(?P<elex>[0-9]{4}[RLDF][0-9]{4})(?P<dsuffix>-[0-9]{8})')


def standard_url(version_url):
    m = CCLXPTN.match(version_url)
    if m is None:
        return version_url
    return BURL + '3' + m.group('elex')


cids = [h.meta.id for h in dm.Search().filter('term', doc_type='cover').scan()]

for k, cid in enumerate(cids):
    if k % 1000 == 0 and k != 0:
        sleep(30)
    c = dm.Cover.get(cid)
    c.source_url = standard_url(c.source_url)
    c.save()
