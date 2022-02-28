import unittest

from views.standard_messages import _standard_messages


class TestStandardMessages(unittest.TestCase):

    langs = sorted(set(_standard_messages.keys()) - {'en'})
    benchmark = set(_standard_messages['en'].keys())

    def test_to(self):
        addeds = {'this_domain', 'This_Domain', 'lexparency_url'}
        for lang in self.langs:
            comparee = set(_standard_messages[lang].keys())
            self.assertEqual(self.benchmark - comparee - addeds, set())

    def test_from(self):
        for lang in self.langs:
            comparee = set(_standard_messages[lang].keys())
            self.assertEqual(comparee - self.benchmark, set())


if __name__ == '__main__':
    unittest.main()
