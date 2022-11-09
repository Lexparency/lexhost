from functools import wraps

from elasticsearch import NotFoundError
from flask import Flask, render_template
from werkzeug.exceptions import NotFound

from views.standard_messages import standard_messages


def not_found(error):
    return (
        render_template(
            "exceptions/404.html",
            title="404",
            messenger=standard_messages,
            message=str(error),
            url=standard_messages["lexparency_url"],
        ),
        404,
    )


def removed(error):
    return (
        render_template(
            "exceptions/410.html",
            title="content removed",
            messenger=standard_messages,
            message=str(error),
            url=standard_messages["lexparency_url"],
        ),
        410,
    )


def forbidden(error):
    return (
        render_template(
            "exceptions/403.html",
            title="403",
            messenger=standard_messages,
            message=str(error),
            url=standard_messages["lexparency_url"],
        ),
        403,
    )


def register_app(app: Flask):
    for code, function in [(404, not_found), (410, removed), (403, forbidden)]:
        app.errorhandler(code)(function)


def convert_exception(from_exc, to):
    """Decorator factory to convert Exception <from_exc> to Exception <to>
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


handle_as_404 = convert_exception(NotFoundError, NotFound)
