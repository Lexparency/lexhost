from time import sleep
import re

from legislative_act import model as dm
from settings import LANG_2, INTERNET_DOMAIN

if LANG_2 == 'en':
    text_with_relevance = 'Text with EEA relevance'
elif LANG_2 == 'de':
    text_with_relevance = 'Text von Bedeutung für den EWR'
else:
    raise NotImplementedError(LANG_2)


unslashed = re.compile(f'https://{INTERNET_DOMAIN}/eu/[A-Z0-9]+(?!/)$')


def cleanse_title(previous):
    previous = previous.strip()
    previous = previous.replace('</p>,', ',</p>')
    previous = previous.replace(' zur</p> ', '</p> zur ')
    previous = previous.replace('<p class=\"lxp-title_essence\">Zur</p>', 'zur')
    previous = previous.replace('<p class=\"lxp-title_essence\"> )', ') <p class=\"lxp-title_essence\">')
    previous = previous.replace(' <p class=\"lxp-title_essence\">)', ') <p class=\"lxp-title_essence\">')
    previous = previous.replace('( ', ' (')
    previous = previous.replace(' sowie zur</p> ', '</p> sowie zur ')
    for initial in (f' ({text_with_relevance})</p>', f' {text_with_relevance}</p>'):
        previous = previous.replace(
            initial,
            f'</p> ({text_with_relevance})')
    previous = previous.replace(
        f' {text_with_relevance}', f' ({text_with_relevance})')
    return previous


def cleanse_title_essence(previous):
    if previous is None:
        return previous
    previous = previous.strip()
    for twr in (f'({text_with_relevance})', text_with_relevance):
        previous = previous.replace(twr, '')
    previous = previous.replace(' (. )', '')
    return previous


def canonicalize_iri(iri):
    iri = iri.replace('http://', 'https://')
    if unslashed.match(iri) is not None:
        return iri + '/'
    return iri


def get_locators():
    s = dm.Search()
    s = s.filter('term', doc_type='cover')
    return [c.meta.id for c in s.scan()]


def fix_title_essence(c: dm.Cover):
    if c.title_essence is None:
        return False
    cleansed = cleanse_title_essence(c.title_essence)
    if cleansed != c.title_essence:
        c.title_essence = cleansed
        return True
    return False


def fix_document_title(c: dm.Cover):
    if c.title is None:
        return False
    cleansed_title = cleanse_title(c.title)
    if cleansed_title != c.title:
        # print(f"{c.abstract.id_local}::  {c.title} ==>> {previous}")
        c.title = cleansed_title
        return True
    return False


def fix_cover_anchors(c: dm.Cover):
    changed = False
    for a_name in dm.Cover.iter_anchors():
        anchors = getattr(c, a_name)
        for anchor in anchors:
            href = anchor.href.replace('/TXT/HTML/?uri=CELEX:',
                                       '/ALL/?uri=CELEX:')
            href = canonicalize_iri(href)
            if href != anchor.href:
                changed = True
                anchor.href = href
            title = cleanse_title_essence(anchor.title)
            if title != anchor.title:
                anchor.title = title
                changed = True
    return changed


def fix_single_cover(c: dm.Cover):
    changed = fix_document_title(c)
    changed = fix_cover_anchors(c) or changed
    changed = fix_title_essence(c) or changed
    return changed


if __name__ == '__main__':
    locators = get_locators()
    print(f'Working through {len(locators)} locators.')
    for n, locator in enumerate(locators):
        if n % 1000 == 0:
            sleep(30)
        cover = dm.Cover.get(locator)
        if fix_single_cover(cover):
            print(f'Saving changes for {locator}', flush=True)
            cover.save()
