from datetime import datetime
import re

from werkzeug.datastructures import MultiDict
from werkzeug.urls import url_encode

from legislative_act.searcher import Filter
from settings import FILTER_TYPES

ACT_TYPES = list(FILTER_TYPES.keys())
year_pattern = re.compile(r"[0-9]{4}$")
date_pattern = re.compile("[0-9]{4}-[0-9]{2}-[0-9]{2}$")


class SearchForm(dict):
    slots = (
        "search_words",
        "type_document",
        "deep",
        "in_force",
        "date_from",
        "date_to",
        "serial_number",
    )

    @classmethod
    def parse(cls, get_dict: MultiDict):
        """Converts the filter-values provided by the GET-request dict to
        python-variables instead of just strings.
        """
        if len(get_dict) == 0:
            return None
        query = {"type_document": get_dict.getlist("type_document")}
        exact_year = get_dict.get("exact_year") == "on"
        for key, value in get_dict.items():
            if value == "":
                continue
            if key in ("type_document", "exact_year"):
                continue
            elif key in ("in_force", "page", "deep", "serial_number"):
                query[key] = eval(value)
            elif key == "search_words":
                if value.strip() != "":
                    query[key] = value
            elif key in ("date_from", "date_to"):
                if year_pattern.match(value):
                    if key == "date_from":
                        query[key] = "{}-01-01".format(value)
                    else:
                        query[key] = "{}-12-31".format(value)
                elif date_pattern.match(value):
                    query[key] = value
            else:
                query[key] = value
        if exact_year and "date_from" in query:
            # noinspection PyUnresolvedReferences
            query["date_to"] = query["date_from"].replace("-01-01", "-12-31")
        return cls(**query)

    def as_filter(self):
        def convert(k, v):
            if k in ("date_from", "date_to"):
                return datetime.strptime(v, "%Y-%m-%d")
            return v

        return Filter(
            **{
                key: convert(key, value)
                for key, value in self.items()
                if (key != "search_words" and key in self.slots)
            }
        )

    @classmethod
    def default(cls):
        return cls(
            search_words="",
            type_document={t: "" for t in ACT_TYPES},
            # TODO: Check if JINJA can handle dictionaries with actual True
            #  and False as dictionary keys. If so: use that feature.
            deep={"False": "", "True": ""},
            in_force={"None": "checked", "True": "disabled", "False": "disabled"},
            date_from="",
            date_to="",
            serial_number="",
        )

    def form_config(self):
        return {
            "search_words": 'value="{}"'.format(self.get("search_words", ""))
            * ("search_words" in self),
            "type_document": {
                t: "checked" * (t in self.get("type_document", [])) for t in ACT_TYPES
            },
            "deep": {
                "False": "checked" * (not self.get("deep", False)),
                "True": "checked" * self.get("deep", False),
            },
            "in_force": {
                "None": "checked" * ("in_force" not in self),
                "True": "disabled" * ("in_force" not in self)
                + " checked" * self.get("in_force", False),
                "False": "disabled" * ("in_force" not in self)
                + " checked" * (not self.get("in_force", True)),
            },
            "date_from": 'value="{}"'.format(self["date_from"][:4])
            if "date_from" in self
            else "",
            "date_to": 'value="{}"'.format(self["date_to"][:4])
            if "date_to" in self
            else "",
            "serial_number": 'value="{}"'.format(self["serial_number"])
            if "serial_number" in self
            else "",
        }

    def repaginator(self, pages, path):
        qd = MultiDict()
        for key, values in self.items():
            if key not in self.slots:
                continue
            if type(values) in (list, tuple):
                for value in values:
                    qd.update({key: value})
            else:
                qd.update({key: values})
        return [
            {
                "role": p[0],
                "page": p[1],
                "href": "{}?{}&page={}".format(path, url_encode(qd), str(p[1])),
            }
            for p in pages
        ]
