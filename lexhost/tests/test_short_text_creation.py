import unittest

from views.read import get_title_overview, get_description_overview, get_title_article, get_description_article

in_2_out = {
    # pop_acronym, pop_title, id_human, id_local
    ('CRR', 'Eigenmittelverordnung', 'Verordnung (EU) 575/2013', '32013R0575'):
        'Eigenmittelverordnung (CRR), Verordnung (EU) 575/2013',
    (None, 'Eigenmittelverordnung', 'Verordnung (EU) 575/2013', '32013R0575'):
        'Eigenmittelverordnung, Verordnung (EU) 575/2013',
    (None, 'Eigenmittelverordnung', None, '32013R0575'):
        'Eigenmittelverordnung, 32013R0575',
    (None, None, 'Verordnung (EU) 575/2013', '32013R0575'):
        'Verordnung (EU) 575/2013',
    ('CRR', None, 'Verordnung (EU) 575/2013', '32013R0575'):
        'CRR, Verordnung (EU) 575/2013',
    ('CRR', None, None, '32013R0575'):
        'CRR, 32013R0575',
}

i2oa = {
    # leaf_ordinate, pop_acronym, pop_title, id_human, id_local, leaf_title
    ('Article 92', 'CRR', 'Eigenmittelverordnung', 'Verordnung (EU) 575/2013',
     '32013R0575', 'Eigenmittelanforderung'): 'Art. 92 CRR - Eigenmittelanforderung',
    ('Article 92', None, 'Eigenmittelverordnung', 'Verordnung (EU) 575/2013',
     '32013R0575', 'Eigenmittelanforderung'): 'Art. 92 Eigenmittelverordnung - Eigenmittelanforderung',
    ('Article 92', None, None, 'Verordnung (EU) 575/2013',
     '32013R0575', 'Eigenmittelanforderung'): 'Art. 92 Verordnung (EU) 575/2013 - Eigenmittelanforderung',
    ('Article 92', None, None, None, '32013R0575',
     'Eigenmittelanforderung'): 'Art. 92 32013R0575 - Eigenmittelanforderung',
    ('Article 92', None, None, 'Verordnung (EU) 575/2013',
     '32013R0575', None): 'Art. 92 Verordnung (EU) 575/2013',
}


class TestShortTextCreation(unittest.TestCase):

    def test_title(self):
        for inp, out in in_2_out.items():
            self.assertEqual(out, get_title_overview(*inp))

    def test_description_overview(self):
        self.assertEqual(
            'Verordnung (EU) Nr. 575/2013 des Europäischen Parlaments und des '
            'Rates vom 26. Juni 2013 Über Aufsichtsanforderungen an Kreditinstitute und Wertpapierfirmen ...',
            get_description_overview(
                'Verordnung (EU) Nr. 575/2013 des Europäischen Parlaments und '
                'des Rates vom 26. Juni 2013 <p class=\"lxp-title_essence\">'
                'Über Aufsichtsanforderungen an Kreditinstitute und '
                'Wertpapierfirmen</p> und zur Änderung der Verordnung (EU) '
                'Nr. 646/2012  (Text von Bedeutung für den EWR)', None, None)
        )

    def test_article_title(self):
        for inp, out in i2oa.items():
            self.assertEqual(out, get_title_article(*inp))

    def test_article_description(self):
        self.assertEqual(
            'Unbeschadet der Artikel 93 und 94 müssen Institute zu jedem '
            'Zeitpunkt folgende Eigenmittelanforderungen erfüllen: eine '
            'harte Kernkapitalquote von 4,5 ...',
            get_description_article(
                '<ol><li data-title="(1)" id="1">Unbeschadet der Artikel '
                '<a href="/eu/32013R0575/ART_93/" data-content-heading="Art. 93">93</a> und '
                '<a href="/eu/32013R0575/ART_94/" data-content-heading="Art. 94">94</a> müssen '
                '<a href="/eu/32013R0575/ART_2/#5" data-content-heading="Definition: Institute">'
                'Institute</a> zu jedem Zeitpunkt folgende Eigenmittelanforderungen erfüllen:<ol>'
                '<li data-title="a)" id="1-a">eine harte Kernkapitalquote von 4,5 %,</li>'
                '<li data-title="b)" id="1-b">eine Kernkapitalquote von 6 %,</li><li data-title="c)" id="1-c">'
                'eine Gesamtkapitalquote von 8 %,</li><li data-title="d)" id="1-d">'
                'eine Verschuldungsquote von 3 %.</li></ol></li>'
                '<li data-title="(1a)" id="1a">Zusätzlich zu der Anforderung '
                'nach Absatz 1 Buchstabe d des vorliegenden Artikels muss ein '
                '<a href="/eu/32013R0575/ART_4/#1-133" data-content-heading="Definition: G-SRI">G-SRI</a> '
                'zu jedem Zeitpunkt einen Puffer der Verschuldungsquote in Höhe '
                'seiner Gesamtrisikopositionsmessgröße nach '
            )
        )


if __name__ == '__main__':
    unittest.main()
