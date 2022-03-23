from pathlib import Path

from django.http import HttpResponseGone

LANG_2 = 'en'
INTERNET_DOMAIN = 'lexparency.org'
DEFAULT_IRI = f'https://{INTERNET_DOMAIN}'

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = Path(__file__).resolve().parent

CACHE_CONFIG = {
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 30
}

FEATURED = {'eu': ('32016R0679', '32013R0575')}

BACKLINKS = [
    'https://lexparency.org/eu/32002F0584/ART_4/latest',
    'https://lexparency.org/eu/32002F0584/TOC/latest',
]

BOTAPI = '_botapi'
DUMP_PATH = r'C:\Users\Martin\lexparency\doq\botapi_dump'

FILTER_TYPES = {
    # TODO: FILTER_TYPES are currently hard coded in the search interface.
    #  Use this configuration instead.
    "REG": "Regulation",
    "DIR": "Directive",
}

TRUSTED_HOSTS = ['127.0.0.1', 'localhost']

LANGUAGE_DOMAIN = [
    {'lang_short': 'de', 'domain': 'lexparency.de', 'display': 'Deutsch'},
    {'lang_short': 'en', 'domain': 'lexparency.org', 'display': 'English'},
]

DEAD_SIMPLE_REDIRECTS = {  # Legacy handling again
    # '/eu/TFEU/': 'https://eur-lex.europa.eu/legal-content/DE/ALL/?uri=CELEX:11957E/TXT',
    '/eu/Regulation_EU_640-2014/': '/eu/32014R0640/',
    '/eu/wtf': '/eu/32013R0575/',
    '/contact_us.php': HttpResponseGone('/contact_us.php')
}

DIAMONDS = {
    '32016R0679': 'GDPR',
    '32013R0575': 'CRR',
}

FOLLOW_DOMAINS = {
    'alternativeassets.club'
}
