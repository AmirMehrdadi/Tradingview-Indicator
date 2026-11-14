"""Parameter-freeze and environment checks; no trading or Bootstrap simulation."""
import copy
import json
import socket
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import numpy as np

from tools.environment_fingerprint import rng_probe
from tools import verify_research_freeze as freeze


class ResearchFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = freeze.load(freeze.ROOT / "configs/research_v0.2.2.json")
        cls.spec = (freeze.ROOT / "STRATEGY_SPEC_v0.2.2.md").read_text(encoding="utf-8")
        cls.instrument = freeze.load(freeze.BASE / "evidence/instrument.json")
        cls.environment = freeze.load(freeze.BASE / "environment.json")

    def validate(self, config):
        freeze.validate_config(config, self.spec, self.instrument)

    def test_official_configuration_matches_frozen_design(self):
        self.validate(self.config)

    def test_official_k_cannot_be_overridden(self):
        for value in ("2.5", 2.0, 3.0, None, True):
            changed = copy.deepcopy(self.config)
            changed["K_cost_stop"] = value
            with self.assertRaises(freeze.FreezeError):
                self.validate(changed)

    def test_costs_are_fixed_and_are_not_account_verified(self):
        for key, value in (("taker_fee_rate_per_side", 0.0002), ("execution_friction_rate_per_fill", 0.0), ("classification", "VERIFIED_ACCOUNT_RATE")):
            changed = copy.deepcopy(self.config)
            changed["cost_assumptions"][key] = value
            with self.assertRaises(freeze.FreezeError):
                self.validate(changed)

    def test_economic_rule_and_inclusive_boundary(self):
        k = Decimal(str(self.config["K_cost_stop"]))
        fraction = Decimal(str(self.config["cost_floor"]["roundtrip_cost_max_fraction_of_planned_stop"]))
        self.assertEqual(k * fraction, Decimal(1))
        self.assertTrue(Decimal(10) / Decimal(4) >= k)
        self.assertFalse(Decimal(10) / Decimal("4.0001") >= k)
        self.assertTrue(Decimal(10) / Decimal("3.9999") >= k)
        self.assertEqual(self.config["cost_floor"]["comparison"], ">=")

    def test_no_candidate_or_holdout_change(self):
        for field in ("candidate_combinations", "partitions_utc"):
            changed = copy.deepcopy(self.config)
            if field == "candidate_combinations":
                changed[field]["C13"] = ["B"]
            else:
                changed[field]["final_holdout"][1] = "2026-12-01T00:00:00Z"
            with self.assertRaises(freeze.FreezeError):
                self.validate(changed)

    def test_historical_units_and_constraints_cannot_silently_change(self):
        for key, value in (("quantity_unit", "USDT"), ("tick_size", "0.01"), ("qty_step", "0.01"), ("historical_effective_dates", "VERIFIED")):
            changed = copy.deepcopy(self.config)
            changed["instrument_assumption"][key] = value
            with self.assertRaises(freeze.FreezeError):
                self.validate(changed)

    def test_entry_minimum_notional_and_closing_exemption(self):
        rules = self.config["instrument_assumption"]["minimum_order_rules"]
        self.assertTrue(rules["entry_market"]["minimum_notional_applies"])
        self.assertTrue(all(rules[name]["minimum_qty_applies"] and not rules[name]["minimum_notional_applies"]
                            for name in ("tp1_reduce_only_limit", "tp2_reduce_only_limit", "protective_stop_close")))
        changed = copy.deepcopy(self.config)
        changed["instrument_assumption"]["minimum_order_rules"] = {}
        with self.assertRaises(freeze.FreezeError):
            self.validate(changed)

    def test_parameter_freeze_is_not_performance_validation(self):
        changed = copy.deepcopy(self.config)
        changed["official_performance_validation_status"] = "VALIDATED"
        with self.assertRaises(freeze.FreezeError):
            self.validate(changed)

    def test_bootstrap_seed_and_engine_remain_pre_registered(self):
        changed = copy.deepcopy(self.config)
        changed["bootstrap_contract_only_not_executed"]["bit_generator"] = "PCG64DXSM"
        with self.assertRaises(freeze.FreezeError):
            self.validate(changed)

    def test_exact_environment_matches_record(self):
        freeze.verify_environment(self.environment)

    def test_environment_drift_is_rejected(self):
        different = copy.deepcopy(self.environment["fingerprint"])
        different["packages"]["numpy"] = "2.0.0"
        with patch.object(freeze, "fingerprint", return_value=different):
            with self.assertRaises(freeze.FreezeError):
                freeze.verify_environment(self.environment)

    def test_pcg64_known_answer_vector(self):
        expected = [17521679607614556524, 3067305778748813469, 7259877267382450566, 3616995976359021698,
                    13585104296775985612, 17302790497870354835, 16964609877431305588, 200944561125493797]
        self.assertEqual(rng_probe()["raw_uint64_size_8"], expected)
        self.assertEqual(rng_probe()["generator_integers"]["values"], [15, 16, 12, 2, 0, 6, 4, 3, 8, 12, 10, 15, 1, 15, 8, 0])

    def test_generator_reset_is_deterministic_without_bootstrap(self):
        a = np.random.Generator(np.random.PCG64(20261114)).integers(0, 17, size=16, dtype=np.int64)
        b = np.random.Generator(np.random.PCG64(20261114)).integers(0, 17, size=16, dtype=np.int64)
        self.assertEqual(a.tolist(), b.tolist())

    def test_future_ui_is_separate_and_experimental(self):
        text = (freeze.ROOT / "docs/FUTURE_INDICATOR_K_REQUIREMENT.md").read_text()
        self.assertIn("EXPERIMENTAL / UNVALIDATED", text)
        self.assertIn("defaulting to **2.5**", text)
        self.assertIn("cannot inherit official research validation", text)
        self.assertNotIn("user_selected_K", self.config)

    def test_all_evidence_verified_with_network_connections_disabled(self):
        with patch.object(socket.socket, "connect", side_effect=AssertionError("Network use forbidden during freeze verification")):
            result = freeze.verify_all()
        self.assertEqual(result["status"], "READY_TO_TAG")
        self.assertEqual(len(result["datasets"]), 4)
        self.assertEqual(result["requests_audited_offline"], 91)
        self.assertFalse(result["stage0b_selection_holdout_executed"])
        self.assertFalse(result["new_market_data_downloaded"])
