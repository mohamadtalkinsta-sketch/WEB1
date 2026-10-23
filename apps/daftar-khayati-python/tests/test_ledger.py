import unittest
from ledger import default_state, make_entry, summarize

class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.card = default_state()["cards"][0]

    def test_starter_cards_exist_without_fake_work(self):
        state = default_state()
        self.assertGreaterEqual(len(state["cards"]), 6)
        self.assertEqual(state["entries"], [])
        self.assertEqual(state["receipts"], [])

    def test_net_wage_calculation(self):
        entry = make_entry(card=self.card, qty="4", price="25000",
                           entry_date="2026-10-23", button_cost="5000",
                           external_cost="2000")
        self.assertEqual(entry["gross"], 100000)
        self.assertEqual(entry["net"], 93000)

    def test_not_charging_buttons_does_not_deduct_cost(self):
        entry = make_entry(card=self.card, qty=2, price=40000,
                           entry_date="2026-10-23", button_cost=3000,
                           charge_buttons=False)
        self.assertEqual(entry["net"], 80000)
        self.assertEqual(entry["button_cost"], 0)

    def test_invalid_quantity_and_price_rejected(self):
        with self.assertRaises(ValueError):
            make_entry(card=self.card, qty=0, price=10, entry_date="2026-10-23")
        with self.assertRaises(ValueError):
            make_entry(card=self.card, qty=1, price=0, entry_date="2026-10-23")

    def test_summary_keeps_received_money_separate(self):
        entry = make_entry(card=self.card, qty=2, price=1000, entry_date="2026-10-23")
        totals = summarize([entry], [{"amount": 800}])
        self.assertEqual(totals["net"], 2000)
        self.assertEqual(totals["received"], 800)
        self.assertEqual(totals["net"] - totals["received"], 1200)

if __name__ == "__main__":
    unittest.main()
