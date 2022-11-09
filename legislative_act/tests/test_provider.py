import os
from unittest import TestCase, main
from lxml import etree as et

from legislative_act import model as dm
from legislative_act.receiver import DocumentReceiver
from legislative_act.provider import DocumentProvider


class DummyRequest:
    def __init__(self, get: dict or None = None):
        self.GET = get or {}


class TestRead(TestCase):
    DATA_PATH = os.path.join(os.path.dirname(__file__), "data")
    DOC_NAMES = (
        "32013R0575",
        # '32002R0006', '32009L0065', '32016R0679'
    )

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
        dp = DocumentProvider('eu', '32016R0679')
        print(dp.get_article('ART_1', 'latest').flat_dict())

    def test_versions_availability(self):
        dp = DocumentProvider('eu', '32016R0679')
        print(dp.versions_availability)

    def test_render_preamble(self):
        # TODO: compare with data/32016R0679/rendered_preamble.htm
        dp = DocumentProvider('eu', '32016R0679')
        print(et.tostring(dp.render_preamble_body(dm.Preamble.get(
            'eu-32016R0679'
        )),
                          encoding='unicode', pretty_print=True))


if __name__ == "__main__":
    main()
