import unittest
import os

from legislative_act import model as dm
from legislative_act.receiver import DocumentReceiver
from views.tests.test_path_responses import ViewsTester

DATA_PATH = os.path.join(os.path.dirname(dm.__file__), 'tests', 'data', 'breg')


class TestLatest(ViewsTester):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        for file_name in ('initial.html', '20190930.html'):
            with open(os.path.join(DATA_PATH, file_name), encoding='utf-8') as f:
                DocumentReceiver.relaxed_instantiation(f.read()).save()

    def test_obsolete_latest(self):
        for path in ('/eu/breg/ART_2/', '/eu/breg/ART_2/latest'):
            response = self.client.get(path, follow_redirects=False)
            relocation = response.location.replace('http://localhost', '')
            self.assertEqual('/eu/breg/ART_2/initial', relocation)

    def test_new_initial(self):
        response = self.client.get('/eu/breg/ART_1a/initial')
        self.assertEqual(404, response.status_code)


if __name__ == '__main__':
    unittest.main()
