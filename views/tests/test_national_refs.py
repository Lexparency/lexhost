import unittest

from legislative_act.model import NationalReference

from views.tests.test_path_responses import ViewsTester
from views.nationals import get_id


class TestNationalReferences(ViewsTester):

    def test(self):
        self.client.post('/_national_ref/eu/32013R0575/', json={
            'data': [{
                'url': 'https://dejure.org/gesetze/WTF',
                'text': 'WTF',
                'country_name': 'Deutschland'
            }]
        })
        id_ = get_id('WTF', 'Deutschland')
        nr = NationalReference.get(id_)
        self.assertEqual(nr.references, ['eu-32013R0575'])
        self.client.post('/_national_ref/eu/32013L0036/', json={
            'data': [{
                'url': 'https://dejure.org/gesetze/WTF',
                'text': 'WTF',
                'country_name': 'Deutschland'
            }]
        })
        self.client.post('/_national_ref/eu/32013R0575/', json={
            'data': [{
                'url': 'https://dejure.org/gesetze/WTF',
                'text': 'WTF',
                'country_name': 'Deutschland'
            }]
        })
        nr = NationalReference.get(id_)
        self.assertEqual(nr.references, ['eu-32013R0575', 'eu-32013L0036'])
        self.client.post('/_national_ref/eu/32013R0575/', json={
            'data': [{
                'url': 'https://buzer.de/2319.html',
                'text': 'WTF',
                'country_name': 'Deutschland'
            }]
        })
        nr = NationalReference.get(id_)
        self.assertEqual(nr.urls, ['https://dejure.org/gesetze/WTF',
                                   'https://buzer.de/2319.html'])

    def test_2(self):
        self.client.post('/_national_ref/eu/', json={
            'data': [
                {
                    'url': 'https://dejure.org/gesetze/WTS',
                    'text': 'WTS',
                    'country_name': 'Deutschland',
                    'target': 'eu-32013R0575'
                },
                {
                    'url': 'https://dejure.org/gesetze/WTS',
                    'text': 'WTS',
                    'country_name': 'Deutschland',
                    'target': 'eu-32013L0036'
                }
            ]
        })
        id_ = get_id('WTS', 'Deutschland')
        nr = NationalReference.get(id_)
        self.assertEqual(nr.references, ['eu-32013R0575', 'eu-32013L0036'])


if __name__ == '__main__':
    unittest.main()
