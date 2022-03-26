from functools import partial

from flask import Flask, request, render_template, redirect, Response, url_for
from flask_caching import Cache
from werkzeug.exceptions import NotFound, Gone
import logging
from cachier import cachier

from index_admin import create_index_admin
from utils import register_redirects
from bot_api import create_botapi
from views.land import get_featured, get_covid, get_recents
from views.search import SearchForm, search_document, search_corpus
from views.read import Read, Diamonds
from views.standard_messages import standard_messages
from views import exceptions
from views.sitemapping import SiteMap

from settings import DEBUG, FEATURED, LANGUAGE_DOMAIN, \
    DEAD_SIMPLE_REDIRECTS, BOTAPI, CACHE_CONFIG, FS_CACHE_DIR, \
    FS_CACHE_STALE_AFTER

logger = logging.getLogger(__name__)

diamonds = Diamonds()
read = Read()
fs_cache = partial(
    cachier,
    cache_dir=FS_CACHE_DIR,
    stale_after=FS_CACHE_STALE_AFTER,
    next_time=True
)


def create_app():
    app = Flask(__name__)
    cache = Cache(app, config=CACHE_CONFIG)
    cache.init_app(app)
    exceptions.register_app(app)
    register_redirects(app, DEAD_SIMPLE_REDIRECTS)

    @app.route('/')
    @fs_cache()
    def landing():
        content = {
            'messenger': standard_messages,
            'title': standard_messages['This_Domain'],
            'description': standard_messages['og_description'],
            'r_path': f'/eu/search',
            'form': SearchForm.default(),
            'filter_visibility': 'w3-hide',
            'featured_acts': get_featured('eu', FEATURED['eu']),
            'covid_acts': get_covid(),
            'recent_acts': get_recents(),
            'languages_and_domains': LANGUAGE_DOMAIN,
            'url_path': '',
            'url': standard_messages['lexparency_url']
        }
        return render_template('land.html', **content)

    @app.route('/<obsolete_document_path>/')
    def handle_obsolete_document_path(obsolete_document_path):
        """ Guess what! Even more legacy path handling. """
        if obsolete_document_path == 'eu':
            return redirect(url_for('landing'), 307)
        raise Gone(obsolete_document_path)

    @app.route('/sitemap.xml')
    @fs_cache()
    def sitemap():
        r = Response(response=SiteMap.build('eu').dump().decode('ascii'),
                     status=200,
                     mimetype="application/xml")
        r.headers["Content-Type"] = "text/xml; charset=utf-8"
        return r

    app.register_blueprint(create_botapi(cache.cached()), url_prefix=f'/{BOTAPI}')
    app.register_blueprint(create_index_admin())

    @app.route('/eu/search')
    def corpus_search():
        if request.args:
            if 'search_words' in request.args:
                if request.args['search_words'].strip() == '':
                    return redirect(request.path, 307)
            else:
                return redirect(request.path, 307)
        return search_corpus(request.path, request.args)

    @app.route('/<domain>/<document_id>/search')
    def document_search(domain, document_id):
        id_local = diamonds.get_canonical(document_id)
        all_versions = request.args.get('all_versions') is not None
        return render_template(
            'search_document.html',
            all_versions=(all_versions * 'checked'),
            **search_document(request.path, domain, id_local,
                              words=request.args.get('search_words', ''),
                              page=int(request.args.get('page', 1)),
                              all_versions=all_versions),
            document_id=document_id,
            version=''
        )

    @app.route('/<domain>/<id_local>/<sub_id>/EN/<version>')
    @app.route('/<domain>/<id_local>/<sub_id>/EN/')
    def legacy(domain, id_local, sub_id, version='latest'):
        try:
            read(domain, id_local, sub_id, version)
        except NotFound:
            raise Gone(request.path)
        return redirect(Read.get_standard_path(domain, id_local, sub_id, version),
                        code=301)

    # noinspection PyUnusedLocal
    @app.route('/<domain>/<document_id>/en/<sub_id>/')
    @app.route('/<domain>/<document_id>/en/<sub_id>')
    def legacy_gones(domain, document_id, sub_id):
        raise Gone(request.path)

    @app.route('/<id_local>/<sub_id>/latest')
    def paying_my_dues(id_local, sub_id):
        """ This is just because I messed up previous canonical tags :/
            So, this is a stupid and annoying type of legacy handling.
            But it's necessary.
        """
        if sub_id.upper().startswith('ARTI'):
            sub_id = 'ART_' + sub_id.split(' ')[1]
        elif sub_id.startswith('Erw') or sub_id.startswith('Rec'):
            sub_id = 'PRE'
        elif sub_id.upper().startswith('ANHANG'):
            splitted = sub_id.split(' ')
            if len(splitted) == 2:
                sub_id = 'ANX_' + splitted[1]
            else:
                sub_id = 'ANX'
        elif sub_id.lower().startswith('fin'):
            sub_id = 'FIN'
        return redirect(f'/eu/{id_local}/{sub_id}/', 301)

    @app.route('/' + standard_messages['impress_path'])
    def about():
        return render_template(f'about.html',
                               title=standard_messages['title_about'],
                               description=standard_messages['title_about'],
                               messenger=standard_messages)

    @app.route('/bot_api_documentation')
    def bot_api_documentation():
        return render_template(f'bot_api_documentation.html',
                               title='Bot-API Documentation',
                               description='Bot-API',
                               messenger=standard_messages)

    @app.route('/' + standard_messages['data_protection_path'])
    def data_protection():
        return render_template(f'data_protection.html',
                               title=standard_messages['data_protection_title'],
                               description=standard_messages['data_protection_title'],
                               messenger=standard_messages)

    Read.register(app)

    return app


if __name__ == '__main__':
    create_app().run(debug=DEBUG)
