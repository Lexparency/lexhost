from unittest import TestCase, main
import os
import json
from lxml import etree as et

from legislative_act.toccordior import ContentsTable


class TestToccordior(TestCase):

    DATA_PATH = os.path.join(os.path.dirname(__file__), "data")

    def setUp(self):
        self.maxDiff = None
        self.es_doc_to_toccordion = []
        for file_name in os.listdir(self.DATA_PATH):
            if not file_name.endswith("_toc.json"):
                continue
            key = file_name[0]
            with open(
                os.path.join(self.DATA_PATH, key + "_toc.json"), encoding="utf-8"
            ) as f:
                toc = ContentsTable.from_es(json.load(f))
            with open(
                os.path.join(self.DATA_PATH, key + "_toccordion.htm"), encoding="utf-8"
            ) as f:
                toccordion = f.read()
            self.es_doc_to_toccordion.append((toc, toccordion))

    def test_toccordior(self):
        for toc, toccordion in self.es_doc_to_toccordion:
            self.assertEqual(
                toccordion,
                et.tostring(
                    toc.toccordior("initial"), pretty_print=True, encoding="unicode"
                ),
            )


if __name__ == "__main__":
    main()
