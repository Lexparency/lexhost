from unittest import main, TestCase
import os
import json
from elasticsearch.exceptions import NotFoundError
from datetime import date
from unittest.mock import Mock

from legislative_act.receiver import DocumentReceiver, dm
from legislative_act.history import DocumentHistory
from legislative_act.tests.test_receiver import ignore_order
from legislative_act.utils import generics
from legislative_act.utils.generics import convert_datetime_patterns, get_today


class TestBase(TestCase):

    DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')

    def setUp(self):
        dm.index.create()

    def tearDown(self):
        dm.index.delete()


class TestHistory(TestBase):

    def setUp(self):
        super().setUp()
        with open(os.path.join(self.DATA_PATH, 'document_1.html'),
                  mode='r') as f:
            self.document_1 = DocumentReceiver.relaxed_instantiation(
                f.read(), logger=Mock())
        with open(os.path.join(self.DATA_PATH, 'document_1a.html'),
                  mode='r') as f:
            self.document_1a = DocumentReceiver.relaxed_instantiation(
                f.read(), logger=Mock())
        with open(os.path.join(self.DATA_PATH, 'document_1_versions.json'),
                  mode='r') as f:
            self.versions_1 = DocumentHistory.from_es(json.load(f))
        with open(os.path.join(self.DATA_PATH, 'document_1_1a_versions.json'),
                  mode='r') as f:
            self.versions_1_1a = DocumentHistory.from_es(json.load(f))
        self.document_1.save()

    def test_initial_version(self):
        dh = DocumentHistory.get(
            '{}-{}'.format(self.document_1.domain, self.document_1.id_local))
        self.assertEqual(self.versions_1.to_dict(), dh.to_dict())

    def test_incorporate(self):
        def sort_exposed_and_hidden(l: list):
            return sorted(l, key=lambda x: (x['sub_id'], x['hidden_version']))
        self.document_1a.save()
        dh = DocumentHistory.get(
            '{}-{}'.format(self.document_1.domain, self.document_1.id_local))
        self.assertEqual(
            sort_exposed_and_hidden(
                self.versions_1_1a.to_dict()['exposed_and_hidden']),
            sort_exposed_and_hidden(dh.to_dict()['exposed_and_hidden'])
        )
        self.assertEqual(self.versions_1_1a.to_dict()['availabilities'],
                         dh.to_dict()['availabilities'])
        for sub_id, is_latest in (('TOC', False), ('ART_1', False),
                                  ('ART_3', False)):
            part = dm.Base.get(
                index=dm.index_name,
                id=f'{self.document_1.domain}-{self.document_1.id_local}-'
                f'{sub_id}-initial')
            self.assertEqual(
                is_latest,
                part.abstract.is_latest,
                f"Discrepancy for 'is_latest' at {sub_id}"
            )

    def test_insert_unavailable(self):
        self.document_1a.save()
        dh = DocumentHistory.get('{}-{}'.format(self.document_1.domain,
                                                self.document_1.id_local))
        dh.insert_unavailable('20171222', date(2017, 12, 22), 'initial')
        expectation = [
            {'version': 'initial', 'date_document': date(2016, 4, 27),
             'date_received': get_today(), 'available': True},
            {'version': '20171222', 'date_document': date(2017, 12, 22),
             'date_received': get_today(), 'available': False},
            {'version': '20171224', 'date_document': date(2017, 12, 24),
             'date_received': get_today(), 'available': True}
        ]
        for expected, actual in zip(expectation, dh.availabilities):
            self.assertEqual(expected, actual.to_dict())

    def test_remove_latest(self):
        self.document_1a.save()
        dh = DocumentHistory.get('{}-{}'.format(self.document_1.domain,
                                                self.document_1.id_local))
        dh.remove_latest()
        dh = DocumentHistory.get('{}-{}'.format(self.document_1.domain,
                                                self.document_1.id_local))
        self.assertEqual(self.versions_1.to_dict(), dh.to_dict())
        self.assertEqual(
            set(part.meta.id for part in self.document_1.iter_parts()),
            set(hit.meta.id for hit in dm.Search()
                .filter('term', abstract__id_local=dh.id_local)
                .filter('term', abstract__domain=dh.domain))
        )

    def test_purge(self):
        self.document_1a.save()
        dh = DocumentHistory.get('{}-{}'.format(self.document_1.domain,
                                                self.document_1.id_local))
        dh.purge()
        self.assertEqual(
            [],
            [hit.meta.id
             for hit in dm.Search()
             .filter('term', abstract__id_local=dh.id_local)
             .filter('term', abstract__domain=dh.domain)]
        )
        self.assertRaises(
            NotFoundError,
            dm.VersionsMap.get,
            "{}-{}".format(dh.domain, dh.id_local)
        )

    def test_in_force_property(self):
        id_trunc = '-'.join((self.document_1.domain, self.document_1.id_local))
        dh = DocumentHistory.get(id_trunc)
        self.assertTrue(dh.in_force)
        cover = dm.Cover.get(id_trunc + "-COV-initial")
        cover.abstract.in_force = False
        cover.save()
        dm.index.refresh()
        self.assertRaises(ValueError, lambda: dh.in_force)
        dh.in_force = False
        self.assertFalse(dh.in_force)


class TestStub(TestBase):

    gt = generics._get_today

    def setUp(self):
        super().setUp()
        generics._get_today = lambda: date(2020, 6, 15)
        with open(os.path.join(TestHistory.DATA_PATH, 'stub1.html'),
                  mode='r') as f:
            self.stub_1 = DocumentReceiver.relaxed_instantiation(
                f.read(), logger=Mock())
        with open(os.path.join(TestHistory.DATA_PATH, 'stub1.json'),
                  mode='r') as f:
            stub = convert_datetime_patterns(json.load(f))['document']
            self.versions_map = stub[0]
            self.cover = stub[1]

    def tearDown(self):
        super().tearDown()
        generics._get_today = type(self).gt

    def test_save_stub(self):
        self.stub_1.save()
        self.assertEqual(*ignore_order(
            self.cover, dm.Cover.get('eu-stub1-COV-initial').to_dict()))
        self.assertEqual(*ignore_order(
            self.versions_map, dm.VersionsMap.get('eu-stub1').to_dict()))


class TestStubsLatest(TestBase):

    DATA_PATH = os.path.join(TestBase.DATA_PATH, '31962R0031')

    def test(self):
        for version in ('initial', '20190101', '20200101'):
            with open(os.path.join(self.DATA_PATH, f"{version}.html")) as f:
                dr = DocumentReceiver.relaxed_instantiation(f.read(),
                                                            logger=Mock())
                dr.save()
        for version in ('initial', '20190101'):
            c = dm.Cover.get(f'eu-31962R0031-COV-{version}')
            self.assertFalse(c.abstract.is_latest)
        c = dm.Cover.get('eu-31962R0031-COV-20200101')
        self.assertTrue(c.abstract.is_latest)


class TestArticleAbrogation(TestBase):

    DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'breg')

    def setUp(self):
        super().setUp()
        for file_name in ('initial.html', '20190930.html'):
            with open(os.path.join(self.DATA_PATH, file_name), encoding='utf-8') as f:
                DocumentReceiver.relaxed_instantiation(f.read()).save()

    def test(self):
        art_2 = dm.Article.get('eu-breg-ART_2-initial')
        self.assertEqual(art_2.abstract.version, ['initial'])
        self.assertFalse(art_2.abstract.in_force)
        art_1a = dm.Article.get('eu-breg-ART_1a-20190930')
        self.assertEqual(art_1a.abstract.version, ['20190930'])


class TestConsistentRelation(TestArticleAbrogation):

    def setUp(self):
        super().setUp()
        with open(os.path.join(self.DATA_PATH, os.pardir, 'amends_breg.html'), encoding='utf-8') as f:
            DocumentReceiver.relaxed_instantiation(f.read()).save()

    def test(self):
        c = dm.Cover.get('eu-breg-COV-20190930')
        self.assertEqual(
            [dm.Anchor(href='https://lexparency.org/eu/ambreg/',
                       text='Reg. 0815a',
                       title='Amending the Breakfast Regulation')],
            c.amended_by
        )


class TestConsistentRelation2(TestArticleAbrogation):

    def setUp(self):
        super().setUp()
        c = dm.Cover.get('eu-breg-COV-20190930')
        c.amended_by = [dm.Anchor(href='https://lexparency.org/eu/ambreg0/',
                                  text='Reg. 0815',
                                  title='First Amending the Breakfast Regulation')]
        c.save()

    def test(self):
        with open(os.path.join(self.DATA_PATH, os.pardir, 'amends_breg.html'), encoding='utf-8') as f:
            DocumentReceiver.relaxed_instantiation(f.read()).save()
        c = dm.Cover.get('eu-breg-COV-20190930')
        self.assertEqual(
            [dm.Anchor(href='https://lexparency.org/eu/ambreg0/',
                       text='Reg. 0815',
                       title='First Amending the Breakfast Regulation'),
             dm.Anchor(href='https://lexparency.org/eu/ambreg/',
                       text='Reg. 0815a',
                       title='Amending the Breakfast Regulation'),
             ],
            c.amended_by
        )


if __name__ == '__main__':
    main()
