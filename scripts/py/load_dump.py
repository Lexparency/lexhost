import os
from sys import argv
import json
from time import sleep

from legislative_act import model as dm


def load_single_dump(file_path):
    with open(file_path) as f:
        hits = [json.loads(line) for line in f.readlines()]

    for hit in hits:
        gcd = dm.GenericContentDocument.from_es(hit)
        gcd.save()


def load_directory(dir_path):
    for file_name in os.listdir(dir_path):
        sleep(5)
        load_single_dump(os.path.join(dir_path, file_name))


if os.path.isdir(argv[1]):
    load_directory(argv[1])
elif os.path.isfile(argv[1]):
    load_single_dump(argv[1])


if __name__ == '__main__':
    print('Done')
