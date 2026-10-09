"""Validate event fidelity, deterministic model integration and offline export."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from migration_animation import from_runs, make_comparison


class EventValidationTests(unittest.TestCase):
    def setUp(self):
        self.coords = {'CA':(36.8,-119.4),'NY':(42.9,-75.5)}
        self.history = pd.DataFrame([
            {'year':2027,'state':'CA','population':1,'inflow':0,'outflow':1,'move_rate':.5},
            {'year':2027,'state':'NY','population':1,'inflow':1,'outflow':0,'move_rate':.5},
            {'year':2028,'state':'CA','population':1,'inflow':0,'outflow':0,'move_rate':0},
            {'year':2028,'state':'NY','population':1,'inflow':0,'outflow':0,'move_rate':0}])
        self.moves = pd.DataFrame([{'year':2027,'origin':'CA','destination':'NY','chain_move':1}])

    def replay(self, **overrides):
        run = {'name':'fixture','history':self.history,'moves':self.moves,'n_agents':2}
        run.update(overrides)
        return from_runs([run],self.coords,target_state='NY',seed=201)

    def test_complete_events_and_zero_move_year(self):
        frames = self.replay().payload['scenarios'][0]['frames']
        self.assertEqual(frames[0]['moves'],[['CA','NY',1]])
        self.assertEqual(frames[1]['moves'],[])
        self.assertEqual(frames[1]['year'],2028)
        self.assertEqual(frames[1]['population'],{'CA':1,'NY':1})

    def test_disabled_event_recording_is_not_zero_migration(self):
        with self.assertRaisesRegex(ValueError,'record_events'):
            self.replay(moves=self.moves.iloc[:0])

    def test_reject_bad_routes_and_flow_totals(self):
        for column,value in [('origin','TX'),('destination','CA')]:
            moves = self.moves.copy()
            moves.loc[0,column] = value
            with self.subTest(column=column), self.assertRaises(ValueError):
                self.replay(moves=moves)
        history = self.history.copy()
        history.loc[1,'inflow'] = 0
        with self.assertRaisesRegex(ValueError,'inflow/outflow'):
            self.replay(history=history)

    def test_reject_incomplete_state_year_and_population(self):
        with self.assertRaisesRegex(ValueError,'one row per state'):
            self.replay(history=self.history.iloc[:-1])
        history = self.history.copy()
        history.loc[0,'population'] = 2
        with self.assertRaisesRegex(ValueError,'populations'):
            self.replay(history=history)
        moves = self.moves.copy()
        moves.loc[0,'year'] = 2030
        with self.assertRaisesRegex(ValueError,'outside'):
            self.replay(moves=moves)

    def test_html_export_escapes_untrusted_labels(self):
        attack = '</script><script>alert(1)</script>'
        replay = self.replay(name=attack)
        content = replay.to_html()
        self.assertNotIn(attack,content)
        self.assertEqual(content.count('<script'),2)
        self.assertNotIn('__MIGRATION_DATA__',content)
        self.assertIn('sandbox="allow-scripts"',replay._repr_html_())
        with tempfile.TemporaryDirectory() as folder:
            path = replay.save(Path(folder) / 'replay.html')
            self.assertEqual(path.read_text(encoding='utf-8'),content)

    def test_comparisons_require_same_annual_horizon(self):
        run = {'name':'first','history':self.history,'moves':self.moves,'n_agents':2}
        short = {**run,'name':'short','history':self.history.iloc[:2]}
        with self.assertRaisesRegex(ValueError,'same years'):
            from_runs([run,short],self.coords,target_state='NY',seed=201)


class ModelIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rebuild_scripts.v8lib import load
        cls.ns = load(Path(__file__).resolve().parents[1] / '0914-1_v8.ipynb')

    def test_deterministic_replay_preserves_model_inputs(self):
        parameters = copy.deepcopy(self.ns['PARAMS'])
        state = self.ns['state_data'].copy(deep=True)
        a = make_comparison(self.ns,n_agents=100,years=3,seed=201)
        b = make_comparison(self.ns,n_agents=100,years=3,seed=201)
        self.assertEqual(a.payload,b.payload)
        self.assertEqual(self.ns['PARAMS'],parameters)
        pd.testing.assert_frame_equal(self.ns['state_data'],state,check_exact=True)
        self.assertEqual(len(a.payload['scenarios']),2)
        for scenario in a.payload['scenarios']:
            self.assertEqual(len(scenario['frames']),3)
            for frame in scenario['frames']:
                self.assertEqual(sum(frame['population'].values()),100)

    def test_replay_matches_direct_original_model(self):
        replay = make_comparison(self.ns,n_agents=100,years=3,seed=201)
        for policy,scenario in zip(['baseline','combined'],replay.payload['scenarios']):
            model = self.ns['PolicySocialABM'](
                self.ns['state_data'],self.ns['cross_policy'](policy,1.0),
                n_agents=100,years=3,seed=201,params=self.ns['PARAMS'].copy(),
                interaction_strength=1.0,record_events=True)
            history,moves,_ = model.run()
            for frame in scenario['frames']:
                annual = moves[moves.year==frame['year']]
                self.assertEqual(frame['moves'],annual[['origin','destination','chain_move']].values.tolist())
                populations = history[history.year==frame['year']].set_index('state')['population'].to_dict()
                self.assertEqual(frame['population'],populations)

    def test_reject_invalid_run_settings(self):
        for setting in [{'n_agents':True},{'years':0},{'seed':-1},{'n_agents':10.5}]:
            with self.subTest(setting=setting), self.assertRaises(ValueError):
                make_comparison(self.ns,**setting)


if __name__ == '__main__':
    unittest.main()
