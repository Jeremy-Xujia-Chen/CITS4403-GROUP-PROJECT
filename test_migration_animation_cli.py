"""Check command-line validation of migration_animation.py without loading the model.

Run from the repository root: python -m unittest -v test_migration_animation_cli
"""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from migration_animation import parse_args


class CliValidationTests(unittest.TestCase):
    def rejected(self, *argv):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as caught:
            parse_args(list(argv))
        self.assertEqual(caught.exception.code, 2)
        return err.getvalue()

    def test_defaults(self):
        args = parse_args([])
        self.assertEqual((args.agents, args.years, args.seed), (600, 12, 201))
        self.assertEqual(args.output, Path('migration_animation.html'))

    def test_small_demonstration_arguments(self):
        args = parse_args(['--agents', '100', '--years', '3', '--seed', '201'])
        self.assertEqual((args.agents, args.years), (100, 3))

    def test_minimum_values_are_accepted(self):
        args = parse_args(['--agents', '2', '--years', '1', '--seed', '0'])
        self.assertEqual((args.agents, args.years, args.seed), (2, 1, 0))

    def test_zero_agents(self):
        self.assertIn('--agents must be at least 2', self.rejected('--agents', '0'))

    def test_one_agent(self):
        self.assertIn('--agents must be at least 2', self.rejected('--agents', '1'))

    def test_negative_agents(self):
        self.assertIn('--agents', self.rejected('--agents', '-5'))

    def test_zero_years(self):
        self.assertIn('--years must be at least 1', self.rejected('--years', '0'))

    def test_negative_seed(self):
        self.assertIn('--seed must not be negative', self.rejected('--seed', '-1'))

    def test_non_integer_agents_use_argparse_error(self):
        self.assertIn('invalid int value', self.rejected('--agents', 'many'))

    def test_output_must_be_html(self):
        self.assertIn('.html', self.rejected('--output', 'animation.txt'))

    def test_output_directory_must_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / 'nope' / 'out.html'
            self.assertIn('does not exist', self.rejected('--output', str(missing)))

    def test_output_in_existing_directory_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = parse_args(['--output', str(Path(tmp) / 'out.html')])
            self.assertEqual(args.output.name, 'out.html')

    def test_first_failure_is_reported_before_loading_anything(self):
        message = self.rejected('--agents', '0', '--years', '0')
        self.assertIn('--agents', message)


if __name__ == '__main__':
    unittest.main()
