from legislative_act.model import index
from elasticsearch.exceptions import RequestError

try:
    index.create()
except RequestError as e:
    if e.error not in ('resource_already_exists_exception',
                       'invalid_index_name_exception'):
        raise e
    print('Well, someone has already created it.')
