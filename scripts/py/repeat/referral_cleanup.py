# coding=utf-8
from functools import partial
from time import sleep

from lexref.reflector import celex_2_id_human

from legislative_act import model as dm
from legislative_act.model import Anchor
from settings import DEFAULT_IRI, LANG_2


a_sort = partial(sorted, key=lambda x: x.href)

inter_2_doc_type = {
    "de": {
        "R": "Verordnung",
        "L": "Richtlinie",
        "D": "Entscheidung",
        "F": "Rahmenbeschluss",
    },
    "en": {
        "R": "Regulation",
        "L": "Directive",
        "D": "Decision",
        "F": "Framework Decision",
    },
    "es": {
        "R": "Reglamento",
        "L": "Directiva",
        "D": "Decisión",
        "F": "Decision Marco",
    },
}[LANG_2]


def zur_2_none(essence):
    if essence is None:
        return
    if essence.lower() == "zur":
        return
    return essence


class CoverCorrector:
    def __init__(self):
        locators = set()
        a_texts = {}

        for h in dm.Search().filter("term", doc_type="cover").scan():
            locators.add(h.meta.id)
            if h.abstract.id_local in a_texts:
                continue
            try:
                a_texts[h.abstract.id_local] = {
                    "text": getattr(
                        h,
                        "id_human",
                        celex_2_id_human(h.abstract.id_local, LANG_2.upper()),
                    ),
                    "title": getattr(h, "pop_acronym", None)
                    or zur_2_none(getattr(h, "title_essence", None))
                    or getattr(h, "title", None),
                }
            except (IndexError, ValueError):
                continue
        for key, value in list(a_texts.items()):
            a_texts[f"{DEFAULT_IRI}/eu/{key}/"] = value
        self.locators = locators
        self.a_texts = a_texts

    def fix_anchor(self, a: dm.Anchor):
        try:
            comp = self.a_texts[a.href]
        except KeyError:
            return False
        changed = False
        if a.text != comp["text"]:
            a.text = comp["text"]
            changed = True
        if a.title != comp["title"]:
            if comp["title"] is not None:
                a.title = comp["title"]
                changed = True
        return changed

    @staticmethod
    def uniquify_list(inp):
        u_list = a_sort({a.href: a for a in inp}.values())
        # just a_sort(inp) == u_list did'nt work :/
        if [a.href for a in inp] == [a.href for a in u_list]:
            # inp fully normalized
            return False
        for _ in range(len(inp)):
            inp.pop()
        for a in u_list:
            inp.append(a)
        return True

    @staticmethod
    def remove_external_ref(inp):
        changed = False
        for k, a in reversed(list(enumerate(inp))):
            if not a.href.startswith(f"{DEFAULT_IRI}/eu/"):
                changed = True
                inp.pop(k)
        return changed

    @staticmethod
    def remove_self_ref(inp, id_local):
        changed = False
        for k, a in reversed(list(enumerate(inp))):
            if a.href.startswith(f"{DEFAULT_IRI}/eu/{id_local}"):
                changed = True
                inp.pop(k)
        return changed

    def remove_404_ref(self, inp):
        changed = False
        for k, a in reversed(list(enumerate(inp))):
            if not (a.href.startswith(DEFAULT_IRI) or a.href.startswith("/eu/")):
                continue
            if a.href not in self.a_texts:
                changed = True
                inp.pop(k)
        return changed

    def fill_anchors(self, inp):
        changed = False
        for a in inp:
            if self.fix_anchor(a):
                changed = True
        return changed

    def fix_single_cover(self, c: dm.Cover):
        changed = False
        if c.title_essence is not None and zur_2_none(c.title_essence) is None:
            c.title_essence = None
            changed = True
        for name in c.iter_anchors():
            referral = getattr(c, name, [])
            if self.uniquify_list(referral):
                changed = True
            if self.remove_self_ref(referral, c.abstract.id_local):
                changed = True
            if self.remove_404_ref(referral):
                changed = True
            if self.fill_anchors(referral):
                changed = True
            if name in ("cites", "cited_by"):
                if self.remove_external_ref(referral):
                    changed = True
            if name in Anchor.changers:
                if self.fill_implemented(referral):
                    changed = True
        return changed

    @staticmethod
    def fill_implemented(anchors):
        changed = False
        for a in anchors:
            if getattr(a, "implemented", None) is None:
                a.implemented = False
                changed = True
        return changed

    def fix(self):
        print(f"Working through {len(self.locators)} locators.")
        for n, locator in enumerate(self.locators):
            if n % 1000 == 0:
                sleep(30)
            cover = dm.Cover.get(locator)
            if self.fix_single_cover(cover):
                print(f"Saving changes for {locator}", flush=True)
                cover.save()


if __name__ == "__main__":
    cc = CoverCorrector()
    cc.fix()
    print("Done")
