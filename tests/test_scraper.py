"""Testy na vzorcích skutečných dat stažených 29. 10. 2026.

Spuštění:  python -m unittest discover tests
"""
import json
import unittest

from scraper import checks, kaufland, lidl, penny
from scraper.match import load_products, match
from scraper.util import norm, parse_pack, price_cz

PRODUCTS = load_products()
BY_ID = {p["id"]: p for p in PRODUCTS}


def kl(title, subtitle, price, unit, old=None, loyal=None, klnr="1", f="2026-10-29", t="2026-11-03", disc=0):
    o = {"offerId": f"{f}.{klnr}.CZ3300", "klNr": klnr, "title": title, "subtitle": subtitle,
         "price": price, "unit": unit, "dateFrom": f, "dateTo": t, "discount": disc}
    if old:
        o["formattedOldPrice"] = old
    if loyal:
        o["loyaltyFormattedPrice"] = loyal
    return o


KAUFLAND_RAW = [
    kl("Dýně máslová", "", 21.9, "1 kg", "34,90", klnr="00029404", disc=37),
    kl("K-Jarmark", "Brambory žluté pozdní\nvarný typ: B", 64.9, "5 kg balení", "89,90", klnr="00153719", disc=27),
    kl("LE & CO", "Uzená kýta", 16.9, "100 g", "25,90", klnr="20918086"),
    kl("Jaroměřický", "Tvaroh měkký", 20, "250 g", "38,90", klnr="00410061", disc=48),
    kl("Ovofit", "Tvarohový dezert s jogurtem\nrůzné druhy", 10, "140 g", "19,90", klnr="20751000"),
    kl("Pragolaktos", "Mléko trvanlivé", 10.9, "1 l", loyal="9,90", klnr="00122424"),
    kl("K-Bio", "Mandlové máslo", 99.9, "250 g", "149,90", klnr="20839052"),
    kl("Varmuža", "Ruské vejce v aspiku", 27.9, "200 g", "35,90", klnr="01206355"),
    kl("Rýže parboiled", "Lagris", 34.9, "1 kg", "72,90", klnr="04002951"),
    kl("Babiččina volba", "Mouka hladká", 39.9, "2 kg", klnr="00148856"),
    kl("Jihlavanka Extra jemná", "Mletá káva", 49.9, "150 g", "109,90", klnr="02407631"),
    kl("Milko", "Bio máslo", 39.9, "150 g", "49,90", klnr="00108144", f="2026-10-07"),
    kl("K-Mistři od fochu", "Vepřová kýta\npultový prodej", 59.9, "cena za 1 kg", "156,90", klnr="63000146"),
    kl("Banány", "", 21.9, "1 kg", "39,90", klnr="09700883", f="2026-10-30", t="2026-11-01"),
    kl("Bohemilk", "Máslo", 29.9, "250 g", loyal="27,90", klnr="00120374", f="2026-11-02"),
]

PENNY_RAW = [
    {"amount": "10", "name": "Vejce čerstvá M z podestýlky Karlova Koruna", "packageLabelKey": "st",
     "volumeLabelShort": "ks", "weightArticle": False, "sku": "88-300602",
     "price": {"crossed": 4990, "regular": {"value": 2990}, "validityStart": "2026-10-29", "validityEnd": "2026-11-03"}},
    {"amount": "200", "name": "Švestky sušené Naturalia", "volumeLabelShort": "g", "weightArticle": False, "sku": "88-167321",
     "price": {"loyalty": {"value": 2990}, "regular": {"value": 3890}, "validityStart": "2026-10-29", "validityEnd": "2026-11-03"}},
    {"amount": "450", "name": "Máslo přepuštěné Ghí Allnature", "volumeLabelShort": "ml", "weightArticle": False, "sku": "88-301272",
     "price": {"crossed": 14990, "regular": {"value": 9990}, "validityStart": "2026-10-29", "validityEnd": "2026-11-03"}},
    {"amount": "100", "name": "Šunka nejvyšší jakosti Řezníkův talíř", "volumeLabelShort": "g", "weightArticle": False, "sku": "88-300003",
     "price": {"crossed": 3190, "regular": {"value": 1990}, "validityStart": "2026-10-29", "validityEnd": "2026-11-03"}},
]


class UtilTests(unittest.TestCase):
    def test_parse_pack(self):
        self.assertEqual(parse_pack("250 g"), (0.25, "kg", False))
        self.assertEqual(parse_pack("5 kg balení"), (5.0, "kg", False))
        self.assertEqual(parse_pack("cena za 1 kg"), (1.0, "kg", True))
        self.assertEqual(parse_pack("3x35 g"), (0.105, "kg", False))
        self.assertEqual(parse_pack("180 g/200 g"), (0.18, "kg", False))
        self.assertEqual(parse_pack("10 ks"), (10.0, "ks", False))
        self.assertEqual(parse_pack("500 ml"), (0.5, "l", False))
        self.assertEqual(parse_pack("20 kusů"), (20.0, "ks", False))
        self.assertIsNone(parse_pack("různé druhy"))

    def test_price_and_norm(self):
        self.assertEqual(price_cz("29,90"), 29.9)
        self.assertEqual(price_cz("1 299,00"), 1299.0)
        self.assertEqual(norm("Máslo  Bohemilk"), "maslo bohemilk")


class MatchTests(unittest.TestCase):
    def cases(self, pairs):
        for name, expected in pairs:
            with self.subTest(name=name):
                self.assertEqual(match(name, PRODUCTS), expected)

    def test_butter_is_not_confused(self):
        self.cases([
            ("Bohemilk Máslo", "maslo"),
            ("Milko Bio máslo", "maslo"),
            ("Dýně máslová", None),
            ("K-Bio Mandlové máslo", None),
            ("Máslo přepuštěné Ghí Allnature", None),
            ("K-Jarmark Podmáslový chléb", "chleb"),
            ("Choceňské Tradiční pomazánkové XXL natur", "pomazankove"),
        ])

    def test_other_products(self):
        self.cases([
            ("Pragolaktos Mléko trvanlivé", "mleko"),
            ("Mléko kondenzované Salko 8% Tatra", None),
            ("Vejce čerstvá M z podestýlky Karlova Koruna", "vejce"),
            ("Varmuža Ruské vejce v aspiku", None),
            ("Jaroměřický Tvaroh měkký", "tvaroh"),
            ("Ovofit Tvarohový dezert s jogurtem", None),
            ("K-Mistři od fochu Vepřová kýta pultový prodej", "veprove"),
            ("LE & CO Uzená kýta", None),
            ("Jihlavanka Extra jemná Mletá káva", "kava"),
            ("K-Jarmark Brambory žluté pozdní", "brambory"),
            ("Banány", "banany"),
            ("Šunka nejvyšší jakosti Řezníkův talíř", "sunka"),
            ("Kuřecí prsní řízky chlazené", "kureci-prsa"),
            ("Kuře Duo, 2 kusy v balení", "kure"),
        ])


class KauflandTests(unittest.TestCase):
    def test_extract_ssr(self):
        payload = {"component": "OfferTemplate", "props": {"offerData": {"cycles": [
            {"categories": [{"offers": KAUFLAND_RAW[:2]}]}]}}}
        html = ("<html><script>window.SSR = window.SSR || {}; window.SSR['abc'] = "
                + json.dumps(payload, ensure_ascii=False) + "</script></html>")
        data = kaufland.extract_ssr(html)
        self.assertEqual(len(kaufland.walk_offers(data["props"]["offerData"])), 2)

    def test_build_filters_by_store(self):
        stores = {"kaufland:CZ1410": {"00120374", "00122424", "00410061"}}
        offers = kaufland.build(KAUFLAND_RAW, stores)
        self.assertEqual(len(offers), 3)
        butter = next(o for o in offers if o["rawId"] == "00120374")
        self.assertEqual(butter["price"], 29.9)
        self.assertEqual(butter["card"], 27.9)
        self.assertEqual(butter["from"], "2026-11-02")
        self.assertEqual((butter["q"], butter["u"]), (0.25, "kg"))
        self.assertEqual(butter["stores"], ["kaufland:CZ1410"])

    def test_meat_counter_note(self):
        o = kaufland.to_offer(KAUFLAND_RAW[12], ["kaufland:CZ1410"])
        self.assertTrue(o["perUnit"])
        self.assertEqual(o["limit"], "Jen u masového pultu")
        self.assertEqual(o["pct"], 62)


class PennyTests(unittest.TestCase):
    def test_slugs(self):
        tree = [{"slug": "vsechny-akce-99000000", "children": [
            {"slug": "web-od-29102026", "children": [{"slug": "web-od-29102026-st-web"}]}]},
            {"slug": "ovoce-17"}]
        self.assertEqual(penny.web_slugs(tree), ["web-od-29102026"])

    def test_to_offer(self):
        eggs = penny.to_offer(PENNY_RAW[0])
        self.assertEqual((eggs["price"], eggs["orig"], eggs["q"], eggs["u"]), (29.9, 49.9, 10.0, "ks"))
        prunes = penny.to_offer(PENNY_RAW[1])
        self.assertEqual((prunes["price"], prunes["card"]), (38.9, 29.9))


class LidlTests(unittest.TestCase):
    def test_flyer_ids(self):
        html = ('<a href="/l/cs/letak/akcni-letak-od-ctvrtka-29-10-1-11-2026/ar/0?lf=HHZ">'
                '<a href="/l/cs/letak/spotrebni-zbozi-26-10-1-11-2026/ar/0">'
                '<a href="/l/cs/letak/akcni-letak-od-ctvrtka-29-10-1-11-2026/ar/0">')
        self.assertEqual(lidl.flyer_ids(html), ["akcni-letak-od-ctvrtka-29-10-1-11-2026"])

    def test_items_to_offers(self):
        flyer = {"name": "x", "offerStartDate": "2026-10-29", "offerEndDate": "2026-11-01"}
        items = [{"name": "Trvanlivé polotučné mléko Madeta", "pack": "1 l", "price": 8.9, "confidence": "high"},
                 {"name": "Vepřová kýta bez kosti", "pack": "cena za 1 kg", "price": 59.9,
                  "valid_from": "2026-10-30", "valid_to": "2026-11-01", "limit": "max. 5 balení"},
                 {"name": "Cereální tyčinka Corny", "pack": "50 g", "price": 10.9, "card_only": True}]
        offers = lidl.items_to_offers(items, flyer, 3)
        self.assertEqual(offers[0]["to"], "2026-11-01")
        self.assertEqual(offers[1]["from"], "2026-10-30")
        self.assertIn("Lidl Plus", offers[2]["limit"])


class CheckTests(unittest.TestCase):
    def test_good_offer_passes(self):
        o = kaufland.to_offer(KAUFLAND_RAW[14], ["kaufland:CZ1410"])
        self.assertEqual(checks.problems(o, BY_ID["maslo"]), [])

    def test_bad_unit_price_is_flagged(self):
        o = kaufland.to_offer(kl("X", "Máslo", 2.9, "250 g"), None)
        self.assertTrue(any("mimo rozsah" in p for p in checks.problems(o, BY_ID["maslo"])))

    def test_unreadable_pack_is_flagged(self):
        o = kaufland.to_offer(kl("X", "Máslo", 29.9, "různé druhy"), None)
        self.assertIn("nepřečtené balení", checks.problems(o, BY_ID["maslo"]))


if __name__ == "__main__":
    unittest.main()
