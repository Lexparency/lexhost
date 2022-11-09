import json
import re
from functools import lru_cache

from dateutil import parser
from collections import Counter, defaultdict
from urllib.parse import urlparse

BOT_LIST = [
    "SemrushBot",
    "ltx71",
    "bingbot",
    "PetalBot",
    "Bytespider",
    "Googlebot",
    "DotBot",
    "SeznamBot",
    "Applebot",
    "MJ12bot",
    "Adsbot",
    "adscanner",
    "UptimeRobot",
    "Barkrowler",
    "CCBot",
    "YandexBot",
    "SemanticScholarBot",
    "Seekport Crawler",
    "facebookexternalhit",
    "VelenPublicWebCrawler",
    "centuryb.o.t9",
    "SEOkicks",
    "serpstatbot.com",
    "AhrefsBot",
    "BLEXBot",
    "Metrics Tools Analytics Crawler",
    "Neevabot",
    "Amazonbot",
    "Mediapartners-Google",
    "InfoTigerBot",
    "GrapeshotCrawler",
    "DataForSeoBot",
    "Exabot",
    "MegaIndex.ru",
]

IGNOREIPS = {"167.86.114.97", "127.0.0.1"}  # sleipnir


with open("/etc/apache2/ipblacklist.conf") as f:
    try:
        JAILEDS = {line.strip().split()[-1] for line in f.read().strip().split("\n")}
    except IndexError:
        JAILEDS = set()


class UnexpectedPattern(Exception):
    pass


class LogEntry:

    __slots__ = [
        "ip_address",
        "timestamp",
        "method",
        "path",
        "protocol",
        "response_code",
        "some_number",
        "referrer",
        "client",
    ]

    bot_pattern = re.compile(r"\b({})\b".format("|".join(BOT_LIST)))

    pattern = re.compile(
        r"(?P<ip_address>[0-9.]+) - - \[(?P<timestamp>.+)] "
        r'"(?P<method>[A-Z]+) (?P<path>[^"]+) (?P<protocol>[^"]+)" '
        r"(?P<response_code>[0-9]+) (?P<some_number>[0-9]+) "
        r'"(?P<referrer>[^"]+)" "(?P<client>[^"]+)"$'
    )

    @property
    def bot_name(self):
        m = self.bot_pattern.search(self.client)
        if m is not None:
            return m.group()
        return None

    def __setattr__(self, key, value):
        if key == "timestamp":
            super().__setattr__(key, parser.parse(value.replace(":", " ", 1)))
        elif key in ("response_code", "some_number"):
            super().__setattr__(key, int(value))
        else:
            super().__setattr__(key, value)

    @property
    def is_search(self):
        return "/search?" in self.path

    @property
    def is_main_request(self):
        if self.response_code in (301, 307, 308):
            return False
        if self.path.startswith("/static/"):
            return False
        if "snippet=" in self.path:
            return False
        return True

    def __init__(self, row):
        m = self.pattern.match(row)
        if m is None:
            raise (UnexpectedPattern("Could not parse " + repr(row)))
        for slot in self.__slots__:
            setattr(self, slot, m.group(slot))


class LogFile(list):
    """Basically a list of log-records"""

    @classmethod
    def from_file(cls, path):
        self = cls()
        unparsed_count = 0
        with open(path, encoding="utf-8") as log:
            for k, line in enumerate(log.readlines()):
                try:
                    self.append(LogEntry(line.strip()))
                except UnexpectedPattern:
                    unparsed_count += 1
        print(f"{unparsed_count} unparseable records.")
        return self

    def __hash__(self):
        return id(self)

    @property
    @lru_cache()
    def ip_2_original_referrer(self):
        result = {}
        for entry in self:
            if entry.ip_address in result:
                continue
            result[entry.ip_address] = entry.referrer
        return result

    @property
    def bot_report(self):
        botquests = [
            r for r in self if r.bot_name is not None and r.ip_address not in IGNOREIPS
        ]
        faileds = [
            f"{r.response_code}, {r.bot_name}"
            for r in botquests
            if r.response_code not in (200, 301, 308, 307)
        ]
        cf = Counter(faileds)
        c = Counter([r.bot_name for r in botquests])
        return {
            "counts": [{"name": name, "count": count} for name, count in c.items()],
            "faileds": [{"name": name, "count": count} for name, count in cf.items()],
        }

    @property
    def user_report(self):
        u_requests = [
            r
            for r in self
            if r.bot_name is None
            and r.is_main_request
            and r.ip_address not in IGNOREIPS
            and r.ip_address not in JAILEDS
        ]
        faileds = [
            f"{r.path}, {r.response_code}, {r.referrer}"
            for r in u_requests
            if r.response_code != 200
            if r.path.startswith("/eu/")
        ]
        users = set(r.ip_address for r in u_requests)
        searches = set(r.path for r in u_requests if r.is_search)
        counter = Counter(r.ip_address for r in u_requests)
        referrer_scores = defaultdict(int)
        for ip, cnt in counter.items():
            if self.ip_2_original_referrer[ip] == "-":
                orig = "-"
            else:
                orig = urlparse(self.ip_2_original_referrer[ip]).hostname
                if orig is not None:
                    orig = ".".join(orig.replace("www.", "").split(".")[:-1])
                else:
                    orig = "-"
            referrer_scores[orig] += cnt
        lengths = sorted(counter.values(), reverse=True)
        mc = counter.most_common(2)
        return {
            "user_requests": len(u_requests),
            "searches": sorted(searches),
            "users": len(users),
            "session_lengths": {
                "max": "{} - {}".format(*mc[0]),
                "sub_max": "{} - {}".format(*mc[1]),
                "bouncer": "{:2.0f}%".format(lengths.count(1) / len(users) * 100),
                "rebouncer": "{:2.0f}%".format(lengths.count(2) / len(users) * 100),
                "average": "{:.1f}".format(sum(lengths) / len(lengths)),
                "median": lengths[int(len(lengths) / 2)],
                "quintian": lengths[int(len(lengths) / 5)],
                "faileds": faileds,
            },
            "referrers": [
                {"referrer": referrer, "score": count}
                for referrer, count in sorted(
                    referrer_scores.items(), key=lambda x: x[1], reverse=True
                )[:3]
            ],
        }

    def errors(self):
        cnt = Counter(r.response_code for r in self if r.response_code >= 500)
        return [{"error_code": v, "count": c} for v, c in cnt.items()]

    def report(self):
        result = {"bots": self.bot_report, "users": self.user_report}
        errors = self.errors()
        if errors:
            result["errors"] = errors
        return json.dumps(result, indent=2)


if __name__ == "__main__":
    from sys import argv

    file_path = "/var/log/apache2/access.log"
    if len(argv) == 2:
        file_path = argv[1]
    lf = LogFile.from_file(file_path)
    print(lf.report())
