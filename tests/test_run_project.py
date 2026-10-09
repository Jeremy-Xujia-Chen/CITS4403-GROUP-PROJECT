"""Check run_project's JSON loading and registry/fit consistency checks.

Run from the repository root: python -m unittest -v test_run_project
"""
import json
import tempfile
import unittest
from pathlib import Path

import run_project

THETA = {'beta_income': 1.0, 'beta_jobs': 2.0, 'beta_rent': -0.5, 'beta_distance': -1.5,
         'beta_education': 0.25, 'beta_childcare': -0.75}
EFFECTS = {'TX': 0.1, 'NY': -0.2, 'FL': 0.3, 'MA': -0.4, 'NC': 0.5, 'IL': -0.6, 'WA': 0.7}


def chosen_theta():
    return list(THETA.values()) + list(EFFECTS.values())


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.config_path = self.dir / 'parameters.json'
        self.irs_path = self.dir / 'irs-fit-report.json'

    def write(self, config=None, irs=None):
        config = {**THETA, 'destination_effects': EFFECTS, 'note': 'Ã©Ã© non-ASCII µ'} if config is None else config
        irs = {'chosen_theta': chosen_theta(), 'note': 'Ã©Ã© non-ASCII µ'} if irs is None else irs
        self.config_path.write_text(json.dumps(config, ensure_ascii=False), encoding='utf-8')
        self.irs_path.write_text(json.dumps(irs, ensure_ascii=False), encoding='utf-8')

    def test_read_json_decodes_non_ascii_as_utf8(self):
        self.write()
        self.assertEqual(run_project.read_json(self.irs_path)['note'], 'Ã©Ã© non-ASCII µ')

    def test_matching_registry_returns_theta_in_order(self):
        self.write()
        config, theta = run_project.load_registry(self.config_path, self.irs_path)
        self.assertEqual(theta, chosen_theta())
        self.assertEqual(config['beta_jobs'], 2.0)

    def test_theta_has_thirteen_entries(self):
        self.write()
        _, theta = run_project.load_registry(self.config_path, self.irs_path)
        self.assertEqual(len(theta), len(run_project.THETA_NAMES) + len(run_project.DESTINATIONS))

    def test_mismatch_with_fit_report_raises(self):
        bad = chosen_theta()
        bad[0] += 1e-9
        self.write(irs={'chosen_theta': bad})
        with self.assertRaisesRegex(ValueError, 'differ'):
            run_project.load_registry(self.config_path, self.irs_path)

    def test_missing_coefficient_is_named(self):
        config = {k: v for k, v in THETA.items() if k != 'beta_rent'}
        config['destination_effects'] = EFFECTS
        self.write(config=config)
        with self.assertRaisesRegex(ValueError, 'beta_rent'):
            run_project.load_registry(self.config_path, self.irs_path)

    def test_missing_destination_effect_is_named(self):
        effects = {k: v for k, v in EFFECTS.items() if k != 'WA'}
        self.write(config={**THETA, 'destination_effects': effects})
        with self.assertRaisesRegex(ValueError, 'destination_effects.WA'):
            run_project.load_registry(self.config_path, self.irs_path)

    def test_shipped_registry_matches_fit_report(self):
        cal = Path(run_project.CAL) / 'reliable-calibration'
        _, theta = run_project.load_registry(cal / 'parameters.json', cal / 'irs-fit-report.json')
        self.assertEqual(len(theta), 13)


if __name__ == '__main__':
    unittest.main()
