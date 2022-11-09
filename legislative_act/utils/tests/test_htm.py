from lxml import etree as et
import unittest
from legislative_act.utils.htm import textify


class TextHtmUtils(unittest.TestCase):
    def test_textify(self):
        input = et.fromstring(
            b"<html><head/><body><h1>Hallo Welt</h1>"
            b"<h2>Und Tschuess</h2><p>Dies ist ein Bei<a>spiel</a>.</p></body></html>",
            parser=et.HTMLParser(),
        )
        output = "Hallo Welt Und Tschuess Dies ist ein Beispiel."
        self.assertEqual(textify(input, simplify_blanks=True), output)


if __name__ == "__main__":
    unittest.main()
