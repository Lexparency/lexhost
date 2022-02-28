from collections import defaultdict
from functools import lru_cache
from urllib.parse import urlparse
from hashlib import sha1

from elasticsearch.exceptions import NotFoundError

from legislative_act import model as dm
from legislative_act.history import flushed
from settings import FOLLOW_DOMAINS

COUNTRIES = {
    'Deutschland',
    'Österreich',
    'BLOG',
}


def url2domain(url):
    domain = urlparse(url).netloc
    if domain.startswith('www.'):
        return domain[4:]
    return domain


def rel_follow(url):
    domain = url2domain(url)
    return domain in FOLLOW_DOMAINS


def get_id(text, country_name):
    if country_name != 'Deutschland':
        text = text + ' - ' + country_name
    return sha1(text.encode('utf-8')).hexdigest()[10:20]


def ref_sort_key(target, overview):
    if overview:
        return len(target.references) * len(target.urls) ** 4
    else:
        try:
            p, g = target['text'].split()
        except ValueError:
            return target['text']
        return g + p


@lru_cache(maxsize=2048)
def _get_nationals(domain, id_local, sub_id):
    if sub_id is None:
        target = f'{domain}-{id_local}'
    else:
        target = f'{domain}-{id_local}-{sub_id}'
    s = dm.Search() \
        .filter('term', doc_type=dm.NationalReference.__name__.lower()) \
        .filter('term', references=target)
    result = defaultdict(list)
    for h in sorted(s.scan(), key=lambda x: ref_sort_key(x, sub_id is None),
                    reverse=sub_id is None):
        result[h.country_name].append({
            'text': h.text,
            'title': getattr(h, 'title', None),
            'platforms': [
                {
                    'name': url2domain(url),
                    'href': url,
                    'rel': 'follow' if rel_follow(url) else 'nofollow',
                }
                for url in h.urls
            ]
        })
    return [{'country_name': country,
             'targets': targets}
            for country, targets in result.items()]


def get_nationals(domain, id_local, sub_id=None):
    if sub_id in ('COV', 'TOC', None):
        return {'cover': _get_nationals(domain, id_local, None)}
    return {'cover': _get_nationals(domain, id_local, None),
            'article': _get_nationals(domain, id_local, sub_id)}


@flushed
def write_nationals(target, url, text, country_name, title=None):
    assert target.count('-') in (1, 2)
    assert country_name in COUNTRIES
    id_ = get_id(text, country_name)
    try:
        nr = dm.NationalReference.get(id_)
    except NotFoundError:
        nr = dm.NationalReference(
            country_name=country_name,
            text=text,
            urls=[url],
            references=[target]
        )
        if title is not None:
            nr.title = title
        nr.meta.id = id_
    else:
        assert text == nr.text
        assert country_name == nr.country_name
        if getattr(nr, 'title', None) is None:
            nr.title = title
        if target not in nr.references:
            nr.references.append(target)
        if url not in nr.urls:
            nr.urls.append(url)
    nr.save()


if __name__ == '__main__':
    print(get_nationals('eu', '32013R0575', f'ART_61'))
