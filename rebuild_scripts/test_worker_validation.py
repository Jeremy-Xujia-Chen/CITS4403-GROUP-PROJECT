"""Check that worker.validate_case rejects bad cases with clear messages.

Uses a small fake namespace, so the notebook is not loaded and no model runs.
Run from the repository root: python -m unittest -v rebuild_scripts.test_worker_validation
"""
import unittest

try:
    from . import worker
except ImportError:
    import worker

NS = {
    "INTERACTION_LEVELS": {"weak": 0.60, "medium": 1.00, "strong": 1.40},
    "POLICY_TYPES": ["baseline", "housing", "employment", "combined"],
    "STATE_CODES": ["CA", "TX", "NY", "FL", "MA", "NC", "IL", "WA"],
    "SHOCK_SCENARIOS": {"housing_boom": [], "job_loss": []},
    "FOCAL_STATE": "TX",
}


class ValidateCaseTests(unittest.TestCase):
    def check_rejected(self, case, *fragments):
        with self.assertRaises(ValueError) as caught:
            worker.validate_case(case, NS)
        for fragment in fragments:
            self.assertIn(fragment, str(caught.exception))

    def test_defaults_are_valid(self):
        worker.validate_case({}, NS)

    def test_full_valid_case(self):
        worker.validate_case({"policy": "combined", "seed": 201, "interaction": "strong",
                              "target_state": "NC", "shock": "job_loss", "n_agents": 600,
                              "years": 12, "intensity": 1.5}, NS)

    def test_unknown_interaction_lists_valid_values(self):
        self.check_rejected({"interaction": "mid"}, "interaction", "'mid'", "medium", "strong", "weak")

    def test_unknown_policy(self):
        self.check_rejected({"policy": "tax"}, "policy", "combined")

    def test_unknown_target_state(self):
        self.check_rejected({"target_state": "ZZ"}, "target_state", "WA")

    def test_unknown_shock(self):
        self.check_rejected({"shock": "flood"}, "shock", "job_loss")

    def test_agent_count_too_small(self):
        self.check_rejected({"n_agents": 1}, "n_agents")

    def test_years_too_small(self):
        self.check_rejected({"years": 0}, "years")

    def test_negative_intensity(self):
        self.check_rejected({"intensity": -0.1}, "intensity")

    def test_capacity_mode_needs_external_rate(self):
        self.check_rejected({"capacity_mode": "shared"}, "external_rate")
        worker.validate_case({"capacity_mode": "shared", "external_rate": 0.09}, NS)

    def test_first_error_is_reported_for_several_bad_fields(self):
        self.check_rejected({"interaction": "mid", "policy": "tax"}, "interaction")

    def test_run_rejects_before_building_a_model(self):
        saved = worker._namespace
        worker._namespace = dict(NS)
        try:
            with self.assertRaises(ValueError):
                worker.run({"interaction": "mid"})
        finally:
            worker._namespace = saved


if __name__ == "__main__":
    unittest.main()
