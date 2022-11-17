import os
from datetime import date
from unittest import TestCase, main

from bs4 import BeautifulSoup
from lxml import etree as et

from legislative_act import model as dm
from legislative_act.receiver import DocumentReceiver
from legislative_act.provider import DocumentProvider


class DummyRequest:
    def __init__(self, get: dict or None = None):
        self.GET = get or {}


class TestRead(TestCase):
    DATA_PATH = os.path.join(os.path.dirname(__file__), "data")
    DOC_NAMES = ("32013R0575", "32002R0006", "32009L0065", "32016R0679")

    @classmethod
    def setUpClass(cls):
        dm.index.create()
        for name in cls.DOC_NAMES:
            with open(os.path.join(cls.DATA_PATH, name + "-initial.html")) as f:
                DocumentReceiver.relaxed_instantiation(f.read()).save()

    @classmethod
    def tearDownClass(cls):
        dm.index.delete()

    def test_recitals(self):
        dp = DocumentProvider('eu', '32013R0575')
        recitals = dp.get_article('PRE', 'initial')
        print(recitals)

    def test_read(self):
        dp = DocumentProvider("eu", "32016R0679")
        article = dp.get_article("ART_1", "initial").flat_dict()
        self.assertSetEqual(
            {
                "doc_type", "body", "score_multiplier", "ordinate", "title",
                "serial_number", "version", "date_publication", "type_document",
                "domain", "in_force", "id_local", "is_latest"
            },
            set(article.keys())
        )
        self.assertTrue(
            "This Regulation lays down rules relating to" in article["body"]
        )

    def test_versions_availability(self):
        dp = DocumentProvider("eu", "32016R0679")
        self.assertEqual(
            [a.to_dict() for a in dp.history.availabilities],
            [
                {
                    "date_received": date.today(),
                    "version": "initial",
                    "date_document": date(2016, 4, 27),
                    "available": True
                }
            ]
        )

    def test_render_preamble(self):
        rendered = os.path.join(
            self.DATA_PATH, "32016R0679_rendered_preamble.htm"
        )
        with open(rendered, encoding="utf-8") as f:
            expected = f.read()
        dp = DocumentProvider("eu", "32016R0679")
        inner = dp.get_article("PRE", "initial").body.dressed
        actual = BeautifulSoup(
            f"<article>{inner}</article>", features="html.parser"
        ).prettify(formatter="html")
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    main()
