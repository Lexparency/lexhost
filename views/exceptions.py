from functools import wraps

from django.shortcuts import render
from elasticsearch import NotFoundError

from django.http import Http404

from lexhost.standard_messages import standard_messages

base_context = {
    'messenger': standard_messages,
    'url': standard_messages['lexparency_url']
}


def not_found(request, exception=None):
    return render(request,
                  'exceptions/404.html',
                  context=dict(title='404', exception=exception, **base_context),
                  status=404
                  )


def forbidden(request, exception=None):
    return render(request,
                  'exceptions/403.html',
                  context=dict(title='403', exception=exception, **base_context),
                  status=403
                  )


def bad_request(request, exception=None):
    return render(request,
                  'exceptions/400.html',
                  context=dict(title='400', exception=exception, **base_context),
                  status=400
                  )


def gone(request, exception=None):
    return render(request,
                  'exceptions/410.html',
                  context=dict(title='410', exception=exception, **base_context),
                  status=400
                  )


def internal_error(request, exception=None):
    return render(request,
                  'exceptions/500.html',
                  context=dict(title='500', exception=exception, **base_context),
                  status=500
                  )


def convert_exception(from_exc, to):
    """ Decorator factory to convert Exception <from_exc> to Exception <to>
        :param from_exc: Exception or tuple of Exceptions, to be handled by this
            converter.
        :param to: Exception to be raised instead of the original one.
    """
    def _convert_exception(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except from_exc as e:
                raise to(repr(e))
        return wrapper
    return _convert_exception


handle_as_404 = convert_exception(NotFoundError, Http404)
