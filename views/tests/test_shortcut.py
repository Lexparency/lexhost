import unittest

from views.search import DeadSimpleShortCut
from views.search.shortcuts import TitledLocation, ShortCutter


def i2p(ids: set):
    return {f"/eu/{id_}/" for id_ in ids}


class TestShortCut(unittest.TestCase):

    tl_display_dict = TitledLocation.get_display_dictionary

    @classmethod
    def setUpClass(cls) -> None:
        TitledLocation.get_cover_display_dictionary = lambda x: x

    @classmethod
    def tearDownClass(cls) -> None:
        TitledLocation.get_cover_display_dictionary = cls.tl_display_dict

    def test_dead_simple_short_cut(self):
        for ordinate in (
            "Verordnung 575/2013",
            "Verordnung (EU) 575/2013",
            "Verordnung No. 575/2013",
            "Verordnung 575/2013/EU",
            "Verordnung (EU) Nr. 575/2013",
        ):
            self.assertEqual(
                i2p({"32013R0575", "32013L0575", "32013D0575", "32013F0575"}),
                set(DeadSimpleShortCut(ordinate).paths),
            )
        self.assertEqual(
            i2p(
                {
                    "32013R0077",
                    "31977R2013",
                    "32013L0077",
                    "31977L2013",
                    "32013D0077",
                    "31977D2013",
                    "32013F0077",
                    "31977F2013",
                }
            ),
            set(DeadSimpleShortCut("Verordnung 77/2013").paths),
        )
        self.assertEqual(
            i2p(
                {
                    "31983R0077",
                    "31977R0083",
                    "31983L0077",
                    "31977L0083",
                    "31983D0077",
                    "31977D0083",
                    "31983F0077",
                    "31977F0083",
                }
            ),
            set(DeadSimpleShortCut("Verordnung 77/83").paths),
        )
        for inter in ("EU", "(EU)", ""):
            self.assertEqual(
                i2p({"31977R0035", "31977L0035", "31977D0035", "31977F0035"}),
                set(DeadSimpleShortCut(f"Verordnung {inter} 77/35").paths),
            )
        self.assertEqual(
            i2p({"32013R0575", "32013L0575", "32013D0575", "32013F0575"}),
            set(DeadSimpleShortCut("Verordnung (EU) Nr. 575/2013").paths),
        )
        self.assertEqual(
            i2p({"32013R0575", "32013L0575", "32013D0575", "32013F0575"}),
            set(DeadSimpleShortCut("VO 575/2013").paths),
        )
        self.assertEqual(
            i2p({"32013R0575", "32013L0575", "32013D0575", "32013F0575"}),
            set(DeadSimpleShortCut("zwei zahlen 2013 575 jo!").paths),
        )
        self.assertEqual(set(), set(DeadSimpleShortCut("Wie bitte?").paths))

    def test_short_cutter(self):
        # case: Reference is directly parseable by the reflector
        self.assertEqual(
            [TitledLocation(href="/eu/32013R0575/", title="Regulation (EU) 575/2013")],
            ShortCutter("Regulation (EU) 575/2013").hits,
        )
        # case: no reference at all
        self.assertEqual([], ShortCutter("Wie bitte?").hits)
        # case: Reference is equal to document context
        self.assertEqual(
            [],
            ShortCutter(
                "Regulation (EU) 575/2013", document_context="/eu/32013R0575/"
            ).hits,
        )
        # case: Reference is not parseable by the reflector:
        self.assertEqual(
            [
                TitledLocation(href="/eu/32013R0575/", title=None),
                TitledLocation(href="/eu/32013L0575/", title=None),
                TitledLocation(href="/eu/32013F0575/", title=None),
                TitledLocation(href="/eu/32013D0575/", title=None),
            ],
            ShortCutter("Verordnung (EU) 575/2013").hits,
        )
        # case: Reference is just a stupid number
        self.assertEqual(
            [TitledLocation(href="/eu/32013R0575/ART_22/", title=None)],
            ShortCutter("22", document_context="/eu/32013R0575/").hits,
        )
        # case: Reference is just a stupid number
        #       and document context is not a valid celex (happens)
        self.assertEqual(
            [TitledLocation(href="/eu/TEU/ART_22/", title=None)],
            ShortCutter("22", document_context="/eu/TEU/").hits,
        )

    def test_redundant_ref(self):
        # case: Reference is just a stupid number,
        #       and document is referenced, although already in document context
        self.assertEqual(
            [TitledLocation(href="/eu/32013R0575/ART_22/", title=None)],
            ShortCutter("22 CRR", document_context="/eu/32013R0575/").hits,
        )


if __name__ == "__main__":
    unittest.main()
