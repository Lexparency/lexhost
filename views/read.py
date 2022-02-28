from functools import lru_cache
from datetime import date
import logging
import re

from flask import Flask, render_template, request, redirect, make_response
from werkzeug.exceptions import NotFound, Gone
from werkzeug.urls import url_encode

from views.exceptions import handle_as_404
from views.nationals import get_nationals
from legislative_act.utils.language_generation import human_date
from legislative_act.utils.generics import Clearable, Singleton
from legislative_act.provider import DocumentProvider
from legislative_act import model as dm

from .standard_messages import standard_messages

from settings import LANG_2, LANGUAGE_DOMAIN, DIAMONDS

tags = re.compile('<[^>]*>')
bracketed = re.compile(r'\([^)]{8,}\)')
article_p = re.compile('artikel|article|artículo', flags=re.I)
ARTa = re.compile('ANX[a-z]')
DIAVALUES = set(DIAMONDS.values())


def strip_title(title):
    if title is not None:
        return bracketed.sub('', tags.sub('', title)).strip()


def get_description_overview(title, id_human, id_local):
    result = strip_title(title) or id_human or id_local or ''
    if len(result) <= 160:
        return result
    return ' '.join(result.strip()[:160].strip().split()[:-1]) + ' ...'


def get_description_article(body):
    result = ' '.join(tags.sub(' ', body[:1000]).strip()[:160].strip().split()[:-1])
    return result.replace('  ', ' ') + ' ...'


def get_title_overview(pop_acronym, pop_title, id_human, id_local):
    result = ''
    if pop_title is not None:
        result += pop_title
        if pop_acronym is not None:
            result += f' ({pop_acronym})'
            if id_human == pop_acronym:  # happens, e.g. for treaties
                return result
        return result + ', ' + (id_human or id_local)
    if pop_acronym is not None:
        return pop_acronym + ', ' + (id_human or id_local)
    return id_human or id_local


def get_title_article(leaf_ordinate, pop_acronym, pop_title, id_human,
                      id_local, leaf_title):
    result = article_p.sub('Art.', leaf_ordinate)
    if pop_acronym in DIAVALUES:
        result += ' ' + pop_acronym
    elif pop_title is not None:
        result += ' ' + pop_title
    elif id_human is not None:
        result += ' ' + id_human
    else:
        result += ' ' + id_local
    if leaf_title is not None:
        return result + ' - ' + leaf_title
    return result


@handle_as_404
def dp_get(domain, id_local):
    return DocumentProvider.get(domain, id_local)


@lru_cache(maxsize=1024)
@handle_as_404
def snippet(domain, document_id, fragment_id, version, snip):
    return DocumentProvider.get(domain, document_id) \
            .get_snippet(fragment_id, version, snip)


class Diamonds(metaclass=Singleton):

    def __init__(self):
        self._forward = dict(**DIAMONDS)
        self._backward = {value: key for key, value in self._forward.items()}
        self._redirect = {v.lower(): v for v in self._forward.values()}

    def get_canonical(self, alias):
        alias = self._redirect.get(alias.lower(), alias)
        return self._backward.get(alias, alias)

    def get_alias(self, id_local):
        id_local = self._redirect.get(id_local.lower(), id_local)
        return self._forward.get(id_local, id_local)


class Read(Clearable, metaclass=Singleton):

    __name__ = 'read'

    def __init__(self):
        """ Class to provide contents-table views and article views. """
        self.logger = logging.getLogger()
        self.diamonds = Diamonds()

    def basic_content(self, dp: DocumentProvider, version):
        version, hidden_version = dp.version_hidden_version(version)
        document_id = self.diamonds.get_alias(dp.id_local)
        if hidden_version is not None:
            toccordion = dp.get_toccordion(hidden_version, version, document_id)
        else:
            toccordion = None
        cover = dp.get_cover(hidden_version or dp.current).flat_dict(crumble=True)
        for ref in cover['referrers']:
            ref['label'] = standard_messages[ref['name']]
        enforced = None
        date_in_force = cover.get('first_date_entry_in_force')
        if date_in_force is not None and cover.get('in_force') is True:
            enforced = date_in_force.date() <= date.today()
        for date_field in dm.Cover.date_fields():
            if date_field in cover:
                cover[date_field] = human_date(cover[date_field], LANG_2)
        return {
            'messenger': standard_messages,
            'cover': cover,
            'toccordion': toccordion,
            'current_version': hidden_version == dp.current,
            'version_is_future_version': dp.is_future_version(version),
            'enforced': enforced,
            'document_title': (cover.get('pop_title')
                               or cover.get('title_essence')
                               or cover.get('title')
                               or cover['id_local']),
            'version': version,
            'hidden_version': hidden_version,
        }

    @lru_cache(maxsize=1024)
    def article(self, document_domain, document_id, sub_id, version):
        dp = DocumentProvider.get(document_domain, document_id)
        base = self.basic_content(dp, version)
        hidden_version = base['hidden_version']
        article = dp.get_article(sub_id, hidden_version).flat_dict()
        try:
            base['cover']['in_force'] = base['cover']['in_force'] \
                                        and ((hidden_version == dp.current)
                                             or article['in_force'])
        except KeyError:
            pass
        content = dict(
            view_type='article',
            neighbours=dp.toc(hidden_version).leaf_to_neighbour[sub_id],
            article=article,
            versions=dp.get_versions_availability(sub_id),
            description=get_description_article(article['body']),
            **base
        )
        if sub_id == 'PRE':  # Make Contentstable the overview.
            content['neighbours']['left'] = {
                'ordinate': standard_messages['TOC_ordinate'], 'id': 'TOC'}
        content['title'] = get_title_article(article['ordinate'],
                                             base['cover'].get('pop_acronym'),
                                             base['cover'].get('pop_title'),
                                             base['cover'].get('id_human'),
                                             document_id, article.get('title'))
        return content

    @lru_cache(maxsize=1024)
    def overview(self, domain, id_local, version):
        document_id = self.diamonds.get_alias(id_local)
        dp = DocumentProvider.get(domain, id_local)
        base = self.basic_content(dp, version)
        version = base['version']
        content = dict(
            view_type='overview',
            versions=dp.get_versions_availability('TOC'),
            heading=base['cover'].get('title') or base['cover'].get('id_human'),
            **base
        )
        if base['toccordion'] is not None:
            content['next'] = f"/{domain}/{document_id}/PRE/"
            if version != 'latest':
                content['next'] += version
        content['title'] = get_title_overview(base['cover'].get('pop_acronym'),
                                              base['cover'].get('pop_title'),
                                              base['cover'].get('id_human'),
                                              base['cover'].get('id_local'))
        content['description'] = get_description_overview(
            base['cover'].get('title'),
            base['cover'].get('id_human'),
            base['cover'].get('id_local'))
        return content

    @lru_cache(maxsize=1024)
    def snippet(self, domain, id_local, fragment_id, version, snip):
        dp = dp_get(domain, id_local)
        version, hidden_version = dp.version_hidden_version(version)
        return snippet(domain, id_local, fragment_id, hidden_version, snip)

    @handle_as_404
    def _call(self, domain, id_local, sub_id, version):
        """ Backend for the actual __call__ method.
            WARNING: This method should not be cached, since it
                makes use of the global variable "request"!
        """
        data = {'url': request.url, 'sub_id': sub_id, 'version': version}
        if sub_id == 'TOC':
            data.update(self.overview(domain, id_local, version))
        else:
            data.update(self.article(domain, id_local, sub_id, version))
        return data

    @staticmethod
    def _document_id_gone(document_id):
        """ Basically legacy handling for lexparency.org """
        if document_id.startswith('Regulation_') \
                or document_id.startswith('Directive_'):
            raise Gone(document_id)

    def __call__(self, domain, document_id, sub_id=None, version=None):
        """ Just a pass-through to allow decoration at __init__
            For the scope of this module, the version-ID "latest" actually
            means "default"-version, which is currently implemented as
            latest available version whose date_document lies in the past.
        """
        r_version = version  # subject to overrides, but need original later
        self._document_id_gone(document_id)
        forwarding = (version == 'latest') \
            or (sub_id == 'TOC' and version in ('latest', None))
        id_local = self.diamonds.get_canonical(document_id)
        if self.diamonds.get_alias(id_local) != document_id:
            document_id = self.diamonds.get_alias(id_local)
            forwarding = True
        if id_local == document_id:  # i.e. canonical doc-ID provided
            if self.diamonds.get_alias(id_local) != id_local:
                document_id = self.diamonds.get_alias(id_local)
                forwarding = True
            elif id_local.startswith('3'):
                if id_local != id_local.upper():
                    # some users type in "32006r1791" or similar ...
                    id_local = id_local.upper()
                    document_id = id_local
                    forwarding = True
        if sub_id is not None:
            if '_' in sub_id:
                sub_trunc = sub_id.split('_')[0].upper() + '_'
                if not sub_id.startswith(sub_trunc) and len(sub_id) > 4:
                    # careful!: some articles have coordinate value e.g.: "72b"
                    sub_id = sub_trunc + sub_id.split('_', 1)[1]
                    forwarding = True
            else:
                if sub_id != sub_id.upper() and ARTa.match(sub_id) is None:
                    sub_id = sub_id.upper()
                    forwarding = True
        sub_id = sub_id or 'TOC'
        version = version or 'latest'
        if 'snippet' in request.args:
            return make_response(
                self.snippet(domain, id_local, sub_id,
                             version, request.args['snippet']))
        if sub_id != 'TOC' and version == 'latest':
            dp = dp_get(domain, id_local)
            leaf_versions = dp.get_leaf_versions(sub_id)
            if not leaf_versions:
                raise NotFound(
                    f'Could not find {domain}, {id_local}, {sub_id}.')
            if dp.current not in leaf_versions:
                version = leaf_versions[-1]
                forwarding = True
        result = self._call(domain, id_local, sub_id, version)
        if version == 'latest' and result['version'] is None:
            # none available
            result['version'] = 'latest'
        if version == 'latest' and result['version'] != 'latest':
            forwarding = True
        version = result['version']
        result.update(self.get_paths(domain, document_id, sub_id, version))
        if forwarding:
            target_url = result['standard_path']
            if len(request.args) > 0:
                target_url += '?' + url_encode(request.args)
            return redirect(
                target_url, code=self.get_redirect_code(r_version, version))
        result['languages_and_domains'] = LANGUAGE_DOMAIN
        result['document_id'] = document_id
        result['nationals'] = get_nationals(domain, id_local, sub_id)
        if result['version'] == 'latest':
            result['version'] = ''
        if sub_id == 'TOC':
            return render_template('read_overview.html', **result)
        return render_template('read_article.html', **result)

    @staticmethod
    def get_redirect_code(request_version, target_version):
        if target_version == 'latest':
            return 301
        elif request_version in (None, 'latest') \
                and request_version != target_version:
            return 307
        return 301

    @staticmethod
    def get_canonical_path(domain, document_id, sub_id):
        if sub_id == 'TOC':
            return f'/{domain}/{document_id}/'
        return f'/{domain}/{document_id}/{sub_id}/'

    @classmethod
    def get_standard_path(cls, domain, document_id, sub_id, version):
        if version == 'latest':
            return cls.get_canonical_path(domain, document_id, sub_id)
        return f'/{domain}/{document_id}/{sub_id}/{version}'

    def get_int_canonical_path(self, domain, document_id, sub_id):
        id_local = self.diamonds.get_canonical(document_id)
        return self.get_canonical_path(domain, id_local, sub_id)

    def get_paths(self, domain, document_id, sub_id, version):
        return {'canonical_path':
                self.get_canonical_path(domain, document_id, sub_id),
                'standard_path':
                self.get_standard_path(domain, document_id, sub_id, version),
                'int_canonical_path':
                self.get_int_canonical_path(domain, document_id, sub_id)}

    @classmethod
    def register(cls, app: Flask):
        self = cls()
        app.route('/<domain>/<document_id>/<sub_id>/<version>')(self)
        app.route('/<domain>/<document_id>/<sub_id>/')(self)
        app.route('/<domain>/<document_id>/')(self)

    @classmethod
    def clear_all_caches(cls):
        super().clear_all_caches()
        DocumentProvider.clear_all_caches()
