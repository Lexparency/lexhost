from unittest import main, TestCase
from unittest.mock import Mock, call
import os
import json
from lxml import etree as et

from legislative_act.receiver import DocumentReceiver
from legislative_act.utils.generics import convert_datetime_patterns, json_serial


def dict_2_string(d: dict) -> str:
    return json.dumps(d, indent=2, default=json_serial, sort_keys=True)


def ignore_order(expected: dict, actual: dict):
    if expected["doc_type"] == "cover":
        # order doesn't matter for these two predicates:
        for key in ("passed_by", "is_about"):
            for d in (expected, actual):
                d[key] = set(d[key])
    return expected, actual


class TestReceiver(TestCase):

    DATA_PATH = os.path.join(os.path.dirname(__file__), "data")

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(cls.DATA_PATH, "document_1.html"), mode="r") as f:
            cls.received_document = DocumentReceiver.relaxed_instantiation(
                f.read(), logger=Mock()
            )
        with open(os.path.join(cls.DATA_PATH, "document_1.json"), mode="r") as f:
            expected = convert_datetime_patterns(json.load(f))
        cls.expected = {doc["_id"]: doc["_source"] for doc in expected["data"]}
        with open(os.path.join(cls.DATA_PATH, "document_1_flat.json"), mode="r") as f:
            expected_flat = convert_datetime_patterns(json.load(f))
        cls.expected_flat = {
            doc["_id"]: doc["_source"] for doc in expected_flat["data"]
        }

    def test_receive(self):
        self.received_document.logger.warning.assert_has_calls(
            [
                call("Missing filter field: date_publication"),
                call("Missing filter field: type_document"),
            ],
            any_order=True,
        )
        received = self.received_document.to_dict()
        self.assertEqual(set(self.expected.keys()), set(received.keys()))
        for key in received.keys():
            try:
                # Setting the is_latest flag is not in scope for this test
                del self.expected[key]["abstract"]["is_latest"]
            except KeyError:
                pass
            expected, actual = ignore_order(self.expected[key], received[key])
            self.assertEqual(expected, actual, f"Problems for {key}")

    def test_flat_dict(self):
        for es_dict in list(self.received_document.iter_parts()):
            expected, actual = ignore_order(
                self.expected_flat[es_dict.meta.id], es_dict.flat_dict()
            )
            self.assertEqual(expected, actual)

    def test_stub(self):
        with open(os.path.join(self.DATA_PATH, "stub1.html"), mode="r") as f:
            stub = DocumentReceiver.relaxed_instantiation(f.read(), logger=Mock())
        stub.logger.warning.assert_has_calls(
            [
                call("Missing filter field: date_publication"),
                call("Missing filter field: type_document"),
            ],
            any_order=True,
        )
        assert len(list(stub.iter_parts())) == 1
        cover = list(stub.iter_parts())[0]
        with open(
            os.path.join(self.DATA_PATH, "stub1_cover_flat_dict.json"), mode="r"
        ) as f:
            flat_cover = json.load(f)
        self.assertEqual(*ignore_order(flat_cover, cover.flat_dict()))


class MinorTests(TestCase):
    dr_init = DocumentReceiver.__init__

    in_2_out = [
        ("#ART_201", "/eu/dummy/ART_201/"),
        ("#ART_201-1", "/eu/dummy/ART_201/#1"),
        ("#ART_201-2-5", "/eu/dummy/ART_201/#2-5"),
        ("#ART_200-note_1", "#note_1"),
        ("#ART_200-note_2", "#note_2"),
    ]

    def setUp(self):
        self.source = et.Element("article", {"id": "ART_200", "class": "lxp-article"})
        for anchor, _ in self.in_2_out:
            self.source.append(et.Element("a", attrib={"href": anchor}))
        self.source.append(et.Element("p", attrib={"id": "ART_200-note_2"}))

        def dummy_init(this, *_):
            this.cover = Mock()
            this.cover.abstract.domain = "eu"
            this.cover.abstract.id_local = "dummy"
            this.source = self.source

        DocumentReceiver.__init__ = dummy_init

    @classmethod
    def tearDownClass(cls):
        DocumentReceiver.__init__ = cls.dr_init

    def test_adapt_references(self):
        dr = DocumentReceiver(self.source, Mock())
        dr._adapt_references()
        for (in_anchor, expected), actual in zip(
            self.in_2_out, self.source.xpath("//a/@href")
        ):
            self.assertEqual(
                expected,
                actual,
                f"'{in_anchor}' was converted to '{actual}',"
                f" but expected '{expected}'.",
            )


if __name__ == "__main__":
    main()
