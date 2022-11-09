import datetime
import functools
from hashlib import sha1
from time import sleep

from elasticsearch_dsl import AttrDict, AttrList


class Clearable:
    @classmethod
    def clear_all_caches(cls):
        for name in dir(cls):
            attribute = getattr(cls, name)
            t_name = type(attribute).__name__
            if isinstance(attribute, cls):
                attribute.clear_all_caches()
            elif t_name not in ("method", "_lru_cache_wrapper"):
                continue
            try:
                getattr(attribute, "cache_clear")()
            except AttributeError:
                pass


def paginator(max_pages, total, current):
    total = min(max_pages, total)
    current = min(total, current)
    if total <= 5:
        return [("x" if k == current else "i", k) for k in range(1, total + 1)]
    if current <= 4:
        pages = [("x" if k == current else "i", k) for k in range(1, min(total, 4) + 1)]
    else:
        pages = [("i", 1), ("i", 2), ("<", current - 1), ("x", current)]
    if total > pages[-1][1]:
        pages.append((">", pages[-1][1] + 1))
    return pages


def get_fallbacker(logger, default=None, exceptions=RuntimeError):
    """Decorator generator to securely execute a function and return a default
        value if something failes

    :param logger: logging.Logger
    :param default: callable or other
         If callable: function to be called when call of primary function fails.
         The result of that function call is returned.
         Else: Value to be returnd
    :param exceptions: Exception or tuple thereof to be handled by this.
    :return: Function decorator that carefully executes the decorated function.
        In case of any failure:
            1. A message is printed to the logger.
            2. The parameter "default" controls further action. See description
            of that parameter.
    """

    def fallbacker_(f):
        @functools.wraps(f)
        def fallbacked(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except exceptions:
                logger.error(
                    "Failed executing {}.{}\n"
                    "Positional arguments: {}\nKeyword arguments: {}".format(
                        f.__module__,
                        f.__name__,
                        ", ".join(map(str, args)),
                        ", ".join(
                            [
                                "({}, {})".format(str(k), str(v))
                                for k, v in kwargs.items()
                            ]
                        ),
                    ),
                    exc_info=True,
                )
                if callable(default):
                    return default(*args, **kwargs)
                return default

        return fallbacked

    return fallbacker_


class ConversionError(Exception):
    pass


def convert_datetime_patterns(in_iter, as_date=True, format_="%Y-%m-%d"):
    def atomic_conversion(inp):
        try:
            result = datetime.datetime.strptime(inp, format_)
        except (ValueError, TypeError):
            raise ConversionError
        if as_date:
            return result.date()
        return result

    pair_iterator = in_iter.items() if type(in_iter) is dict else enumerate(in_iter)

    for key, value in pair_iterator:
        if type(value) in (list, dict):
            convert_datetime_patterns(value, as_date=as_date, format_=format_)
        try:
            in_iter[key] = atomic_conversion(value)
        except ConversionError:
            pass
    return in_iter


def ignore_void_dict(**kwargs):
    return {key: value for key, value in kwargs.items() if value is not None}


def coalesce(first: AttrDict, second: AttrDict):
    assert isinstance(first, AttrDict) and isinstance(second, AttrDict)
    for key in set(dir(first) + dir(second)):
        if not hasattr(second, key):
            continue
        # first_attribute = getattr(first, key)
        elif getattr(first, key) is None:
            setattr(first, key, getattr(second, key))
        elif isinstance(getattr(first, key), AttrList):
            if len(getattr(first, key)) == 0:
                setattr(first, key, getattr(second, key))
        elif isinstance(getattr(first, key), AttrDict):
            coalesce(getattr(first, key), getattr(second, key))


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def _get_today():
    return datetime.date.today()


def get_today():
    return _get_today()


def retry(exceptions, tries=2, wait=None):
    """Decorator factory creates retry-decorators which repeats the function
    execution until it finally executes without throwing an exception
    or until the max number of attempts <tries> is reached.
    If <wait> is provided, the process waits that amount of seconds before
    going for the next attempt.
    """

    def decorator(f):
        @functools.wraps(f)
        def protegee(*args, **kwargs):
            for attempt in range(tries):
                try:
                    return f(*args, **kwargs)
                except exceptions:
                    if attempt == tries - 1:  # Exception in final attempt
                        raise
                    if wait is not None:
                        sleep(wait)

        return protegee

    return decorator


def binary_hash(value: bytes) -> bool:
    return int(sha1(value).hexdigest()[-1], 16) % 2 == 0
