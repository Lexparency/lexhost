from unittest import TestCase, main
import json
import os

from legislative_act.utils import paginator


class TestPaginator(TestCase):
    DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')

    def file_path(self, name):
        return os.path.join(self.DATA_PATH, name)

    def setUp(self):
        with open(self.file_path('paginator.json')) as f:
            self.expectations = json.load(f)['expectations']
        for result in self.expectations:
            result['result'] = list(map(tuple, result['result']))

    def test_paginator(self):
        for example in self.expectations:
            self.assertEqual(
                example['result'],
                paginator(
                    example['max_pages'], example['total'], example['current'])
            )


if __name__ == '__main__':
    main()
