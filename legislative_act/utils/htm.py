import re
from lxml import etree as et
from html import escape


blanks = re.compile(r"[\s\n\r\t]+")


def textify(element: et.ElementBase, with_tail=True, simplify_blanks=False):
    """Basically a wrapper of the tostring function from lxml.etree
    ATTENTION: The pretty-printing is necessary. Otherwise,
    the text-content of neighbouring h1 and h2 elements
    (as example) would be glued together.
    """
    if simplify_blanks:
        return blanks.sub(
            " ",
            et.tostring(
                et.fromstring(
                    et.tostring(
                        element,
                        pretty_print=True,
                        with_tail=with_tail,
                        encoding="unicode",
                    ),
                    parser=et.HTMLParser(remove_blank_text=True, remove_comments=True),
                ),
                method="text",
                with_tail=with_tail,
                encoding="unicode",
            ),
        ).strip()
    else:
        return et.tostring(
            element, method="text", encoding="unicode", with_tail=with_tail
        ).strip()


def strip_html(element_string):
    element = et.fromstring(
        "<div>{}</div>".format(element_string), parser=et.HTMLParser()
    )
    return textify(element, simplify_blanks=True)


def is_negligible(in_text):
    """ " Checks if text or tail of XML element is either empty string or None"""
    if in_text is None:
        return True
    elif type(in_text) is str:
        if in_text.strip(chr(160) + " \t\n\r") == "":
            return True
        else:
            return False
    else:
        raise TypeError


def inner_tostring(
    element, skip_ns_declarations=False, simplify_blanks=False, **kwargs
):
    def do_skips(res: str) -> str:
        declarations = [
            ' xmlns:{}="{}"'.format(key, value) for key, value in element.nsmap.items()
        ]
        for declaration in declarations:
            res = res.replace(declaration, "")
        return res

    if kwargs.get("with_tail", False):
        raise RuntimeError(
            "Converting an element's inner to string assumes with_tail=False"
        )
    result = ("" if is_negligible(element.text) else escape(element.text)) + "".join(
        [
            et.tostring(sub_element, encoding="unicode", **kwargs)
            for sub_element in element.xpath("./*")
        ]
    )
    if skip_ns_declarations:
        result = do_skips(result)
    if simplify_blanks:
        result = blanks.sub(" ", result)
    return result.strip()


def undress(dressed):
    if type(dressed) is str:
        return strip_html(dressed)
    elif et.iselement(dressed):
        return textify(dressed, simplify_blanks=True, with_tail=False)
