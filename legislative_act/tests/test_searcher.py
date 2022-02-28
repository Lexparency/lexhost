from unittest import main, TestCase
import os
import json

from legislative_act.receiver import DocumentReceiver, dm
from legislative_act.searcher import CorpusSearcher, DocumentSearcher, Filter


class TestSearcher(TestCase):

    DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')
    data_docs = ('32010R0001', '32010R0001-20120101')

    def file_path(self, name):
        return os.path.join(self.DATA_PATH, name)

    def setUp(self):
        dm.index.create()
        for doc in self.data_docs:
            with open(os.path.join(self.DATA_PATH, doc + '.html')) as f:
                DocumentReceiver.relaxed_instantiation(f.read()).save()
        dm.index.flush()
        self.expectations = {}
        for search_type in ('full_body', 'document'):
            with open(self.file_path(search_type + '_search.json')) as f:
                self.expectations[search_type] = json.load(f)['expectations']
            for exp in self.expectations[search_type]:
                exp['result']['pages'] = list(map(tuple,
                                                  exp['result']['pages']))

    def tearDown(self):
        dm.index.delete()

    def test_full_body_search(self):
        # TODO: test more filters
        for expectation in self.expectations['full_body']:
            self.assertEqual(
                CorpusSearcher(
                    expectation['words'], Filter(deep=True)).get_page(1),
                expectation['result']
            )

    def test_document_search(self):
        for expectation in self.expectations['document']:
            self.assertEqual(
                expectation['result'],
                DocumentSearcher(
                    expectation['words'],
                    'eu',
                    expectation['id_local'],
                ).get_page(1)
            )


if __name__ == '__main__':
    main()
