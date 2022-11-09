import json
import unittest
import os
from datetime import date

from app import create_app, diamonds
from legislative_act import model as dm
from legislative_act.provider import DocumentProvider
from legislative_act.receiver import DocumentReceiver
from settings import BOTAPI
from views.read import Read

BREG_PATH = os.path.join(os.path.dirname(dm.__file__), "tests", "data", "breg")

url_to_redirect = [
    ("/eu/32013R0575/ART_2/EN/", "/eu/32013R0575/ART_2/", 301),
    ("/eu/32013R0575/ART_2/EN", "/eu/32013R0575/ART_2/EN/", 308),
    ("/eu/32013R0575/ART_2/latest", "/eu/32013R0575/ART_2/", 301),
    ("/eu/32013R0575/ART_2", "/eu/32013R0575/ART_2/", 308),
    ("/eu/32013R0575/TOC/", "/eu/32013R0575/", 301),
    ("/eu/32013R0575/TOC/latest", "/eu/32013R0575/", 301),
    ("/eu/breg/", "/eu/breg/TOC/initial", 307),
    ("/eu/32013R0575", "/eu/32013R0575/", 308),
    ("/eu/32019r1981/", "/eu/32019R1981/", 301),
]

urls_to_status = [
    ("/eu/Regulation_EU_2575-2013/Article_10/", 410),
    ("/eu/31990L0630/ART_10/", 404),
    ("/eu/31990L0630/ART_10/whatever", 404),
    ("/eu/31990L0630/", 404),
    ("/eu/32013R0575/ART_1000/", 404),
    ("/eu/32013R0575/ART_2/20200407", 404),
    ("/eu/Regulation_EC_2434-2000/Article_9/", 410),
    ("/eu/Directive_87-566-EEC/en/Article_1", 410),
    ("/eu/Directive_87-566-EEC/en/Article_1/", 410),
    ("/eu/32013R0575/ART_1/EN/initial", 301),
    ("/eu/32013R0575/ART_1/EN/", 301),
    ("/eu/32013R0595/ART_1/EN/", 410),
    ("/eu/32013R0595/ART_1/EN/20200410", 410),
    ("contact_us.php", 410),
]


DATA_PATH = os.path.join(os.path.dirname(__file__), "data")


class ViewsTester(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dm.index.create()
        diamonds._forward = {}
        diamonds._backward = {}

    @classmethod
    def tearDownClass(cls):
        dm.index.delete()

    def setUp(self):
        Read.clear_all_caches()
        DocumentProvider.clear_all_caches()
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def get_relocation(self, entry_path):
        response = self.client.get(entry_path, follow_redirects=False)
        return response.location.replace("http://localhost", ""), response.status_code


class TestViews(ViewsTester):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for file_name in ("32013R0575-initial.html", "32019R1981-initial.html"):
            with open(os.path.join(DATA_PATH, file_name), encoding="utf-8") as f:
                DocumentReceiver.relaxed_instantiation(f.read()).save()
        for file_name in ("initial.html", "20191001.html"):
            with open(os.path.join(BREG_PATH, file_name), encoding="utf-8") as f:
                DocumentReceiver.relaxed_instantiation(f.read()).save()

    def setUp(self):
        super().setUp()
        self.maxDiff = None
        with open(
            os.path.join(DATA_PATH, "path_2_snippet.json"), encoding="utf-8"
        ) as f:
            data = json.load(f)
        self.path2snippet = {i["path"]: i["snippet"] for i in data["path_2_snippet"]}
        with open(os.path.join(DATA_PATH, "dbmap.json"), encoding="utf-8") as f:
            self.dbmap = json.load(f)
        self.dbmap["date"] = date.today().strftime("%Y-%m-%d")
        with open(os.path.join(DATA_PATH, "sitemap.xml"), encoding="utf-8") as f:
            self.expected_sitemap = f.read().replace(
                "2020-02-16", date.today().strftime("%Y-%m-%d")
            )

    def test_redirects(self):
        for entry_url, expected_url, status_code in url_to_redirect:
            response = self.client.get(entry_url, follow_redirects=False)
            relocation = response.location.replace("http://localhost", "")
            self.assertEqual(expected_url, relocation, f"Failed for {entry_url}")
            self.assertEqual(
                status_code, response.status_code, f"Failed for {entry_url}"
            )

    def test_status(self):
        for url, status in urls_to_status:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status)

    def test_snippet(self):
        for path, snippet in self.path2snippet.items():
            self.assertEqual(snippet, self.client.get(path).data.decode("utf-8"))
        for path in ("/eu/32013R0575/ART_9v/?snippet=z", "/eu/CHAR/?snippet=0"):
            r = self.client.get(path)
            self.assertEqual(r.status_code, 404)

    search_hit_tag = '<div id="search-hit-{0}" class="w3-container search-hit">'.format

    def test_document_search(self):
        content = self.client.get(
            "/eu/32013R0575/search?search_words=prudential"
        ).data.decode("utf-8")
        self.assertTrue(self.search_hit_tag(1) in content)
        self.assertFalse(self.search_hit_tag(2) in content)

    def test_corpus_search(self):
        response = self.client.get("/eu/search?search_words=prudential")
        content = response.data.decode("utf-8")
        for i in range(1, 3):
            self.assertTrue(self.search_hit_tag(i) in content)
        self.assertFalse(self.search_hit_tag(3) in content)

    def test_stubbed(self):
        response = self.client.get("/eu/32019R1981/TOC/latest", follow_redirects=False)
        relocation = response.location.replace("http://localhost", "")
        self.assertEqual("/eu/32019R1981/", relocation)
        self.assertEqual(response.status_code, 301)
        response = self.client.get("/eu/32019R1981/", follow_redirects=True)
        self.assertTrue(
            b"Unfortunately, this document is not yet available here." in response.data
        )

    def test_dbmap(self):
        self.assertEqual(
            self.dbmap, json.loads(self.client.get(f"/{BOTAPI}/dbmap.json").data)
        )

    def test_sitemap(self):
        self.assertEqual(
            self.expected_sitemap, self.client.get("/sitemap.xml").data.decode("utf-8")
        )

    def test_domain_to_landing(self):
        self.assertEqual(self.get_relocation("/eu/"), ("/", 307))


class TestDiamonds(ViewsTester):

    botapi = {}
    for fn in (
        "botapi_recents.json",
        "botapi_document_crr.json",
        "botapi_single_step_crr.json",
    ):
        with open(os.path.join(DATA_PATH, fn), encoding="utf-8") as f:
            botapi[fn[7:-5]] = json.load(f)

    def setUp(self):
        super().setUp()
        self.maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with open(
            os.path.join(DATA_PATH, "32013R0575-initial.html"), encoding="utf-8"
        ) as f:
            DocumentReceiver.relaxed_instantiation(f.read()).save()
        diamonds._forward = {"32013R0575": "CRR"}
        diamonds._backward = {"CRR": "32013R0575"}

    canonical_2_entry = {
        "/eu/CRR/": [
            "/eu/32013R0575/",
            "/eu/crr/",
            "/eu/32013R0575/TOC/",
            "/eu/32013R0575/TOC/latest",
        ],
        "/eu/CRR/ART_2/": [
            "/eu/32013R0575/ART_2/",
            "/eu/32013R0575/art_2/",
            "/eu/32013R0575/ART_2/latest",
        ],
        "/eu/CRR/PRE/": ["/eu/32013R0575/prE/"],
        "/eu/CRR/ART_2/initial": ["/eu/32013R0575/ART_2/initial"],
    }

    def test_redirects(self):
        for canonical, entries in self.canonical_2_entry.items():
            for entry in entries:
                target, code = self.get_relocation(entry)
                self.assertEqual(canonical, target)
                self.assertEqual(301, code)

    def test_bare_search(self):
        r = self.client.get("/eu/search")
        self.assertEqual(200, r.status_code)

    def test_botapi_recents(self):
        r = self.client.get("/_botapi/recents.json?date_from=2009-01-01")
        self.assertEqual(self.botapi["recents"], json.loads(r.data.decode("utf-8")))

    def test_botapi_recents_single_step(self):
        r = self.client.get("/_botapi/recents.json?date_from=2009-01-01&single_step")
        self.assertEqual(
            self.botapi["single_step_crr"], json.loads(r.data.decode("utf-8"))
        )

    def test_botapi_document(self):
        r = self.client.get("/_botapi/CRR.json")
        self.assertEqual(
            self.botapi["document_crr"], json.loads(r.data.decode("utf-8"))
        )


class TestMissingInForce(ViewsTester):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with open(
            os.path.join(DATA_PATH, "32013R0575-initial.html"), encoding="utf-8"
        ) as f:
            content = f.read().replace(
                '<meta property="eli:in_force" content="true" datatype="xsd:boolean">',
                "",
            )
            DocumentReceiver.relaxed_instantiation(content).save()

    def test_overview(self):
        r = self.client.get("/eu/32013R0575/")
        self.assertTrue(b'inForceSign"' not in r.data)

    def test_articles(self):
        for art in ("ART_1", "ART_2", "ANX_I"):
            r = self.client.get(f"/eu/32013R0575/{art}/")
            self.assertTrue(b' inForceSign"' not in r.data)


class TestRecentsSingleStep(ViewsTester):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for file_name in ("initial.html", "20190930a.html"):
            with open(os.path.join(BREG_PATH, file_name), encoding="utf-8") as f:
                DocumentReceiver.relaxed_instantiation(f.read()).save()

    def setUp(self):
        super().setUp()
        with open(
            os.path.join(DATA_PATH, "botapi_single_step.json"), encoding="utf-8"
        ) as f:
            self.expected = json.load(f)

    def test_botapi_recents_single_step(self):
        r = self.client.get("/_botapi/recents.json?date_from=2019-09-15&single_step")
        self.assertEqual(self.expected, json.loads(r.data.decode("utf-8")))


if __name__ == "__main__":
    unittest.main()
