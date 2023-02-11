import unittest

from bot_api.views import extract_amends


class ClassExtractAmends(unittest.TestCase):
    def test(self):
        for in_, out_ in [
            ("Approval of the active substance", None),
            (
                "Amendment to Regulation (EU) 540/2011",
                "https://lexparency.org/eu/32011R0540/"
            ),
            ('https://lexparency.org/eu/32011R0540/', None)
        ]:
            self.assertEqual(extract_amends(in_), out_)
