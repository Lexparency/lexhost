from functools import wraps
from typing import Dict, Union

from django.core.exceptions import PermissionDenied


from legislative_act.history import DocumentHistory
from settings import TRUSTED_HOSTS
from .apps.exceptions import handle_as_404


def check_trustworthy(f):
    """
    This security check is based on this expert opinion:
    https://security.stackexchange.com/questions/37481/
    """
    @wraps(f)
    def mistrust(request, *args, **kwargs):
        if request.remote_addr not in TRUSTED_HOSTS:
            raise PermissionDenied('You should not do that!')
        return f(*args, **kwargs)
    return mistrust


def register_redirects(app: Flask, mapping: Dict[str, Union[str, Exception]]):
    """ Basically for handling of legacy paths. """

    for path, target in mapping.items():

        def f():
            if isinstance(target, Exception):
                raise target
            return redirect(target, 301)

        f.__name__ = 'simple_redirect_for_' + str(abs(hash(path)))
        app.route(path)(f)


@handle_as_404
def get_document_history(domain, id_local) -> DocumentHistory:
    return DocumentHistory.get('-'.join((domain, id_local)))
