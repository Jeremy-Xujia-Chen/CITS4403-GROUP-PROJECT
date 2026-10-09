"""Offline animation of accepted moves recorded by the notebook's existing ABM."""
from __future__ import annotations

import argparse
import html
import json
import math
from dataclasses import dataclass
from numbers import Integral
from pathlib import Path


@dataclass
class MigrationAnimation:
    """Self-contained browser document, also displayable in a trusted notebook."""
    payload: dict

    def to_html(self):
        template = Path(__file__).with_name('migration_animation_template.html').read_text(encoding='utf-8')
        # Data cannot terminate the JSON script element or create HTML markup.
        data = json.dumps(self.payload, ensure_ascii=True, allow_nan=False)
        data = data.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
        return template.replace('__MIGRATION_DATA__', data)

    def save(self, path='migration_animation.html'):
        destination = Path(path)
        destination.write_text(self.to_html(), encoding='utf-8')
        return destination

    def _repr_html_(self):
        return ('<iframe title="Simulated interstate migration" sandbox="allow-scripts" '
                'style="width:100%;height:850px;border:0;border-radius:16px" srcdoc="'
                + html.escape(self.to_html(), quote=True) + '"></iframe>')


def from_runs(runs, coordinates, *, target_state, seed):
    """Serialize complete yearly histories and accepted move logs, without sampling.

    Each run supplies ``name``, ``history``, ``moves`` and ``n_agents``. Population
    is the model's end-year population; demographic replacements are not moves.
    A missing event log is rejected rather than shown as zero migration.
    """
    states = list(coordinates)
    if target_state not in states or not states:
        raise ValueError('The target state must have coordinates.')
    locations = {}
    for state, (lat, lon) in coordinates.items():
        if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError('State coordinates must be finite latitude/longitude pairs.')
        locations[str(state)] = [float(lat), float(lon)]
    scenarios = []
    shared_years = None
    for run in runs:
        history, moves = run['history'], run['moves']
        required = {'year', 'state', 'population', 'inflow', 'outflow', 'move_rate'}
        if not required.issubset(history.columns) or history.empty:
            raise ValueError('A complete yearly state history is required.')
        if not {'year', 'origin', 'destination'}.issubset(moves.columns):
            raise ValueError('Use record_events=True to provide the accepted move log.')
        n_agents = int(run['n_agents'])
        if n_agents < 1:
            raise ValueError('n_agents must be positive.')
        years = sorted(int(y) for y in history['year'].unique())
        if years != list(range(years[0], years[-1] + 1)):
            raise ValueError('History years must be contiguous.')
        if shared_years is not None and shared_years != years:
            raise ValueError('Compared scenarios must cover the same years.')
        shared_years = years
        if not set(moves['year']).issubset(years):
            raise ValueError('Move log contains a year outside the history.')
        frames = []
        for year in years:
            rows = history[history['year'] == year]
            if len(rows) != len(states) or set(rows['state']) != set(states):
                raise ValueError('Every year must have exactly one row per state.')
            indexed = rows.set_index('state')
            population = {s: int(indexed.loc[s, 'population']) for s in states}
            if min(population.values()) < 0 or sum(population.values()) != n_agents:
                raise ValueError('State populations must sum to the simulated population.')
            annual = moves[moves['year'] == year]
            expected = float(rows.iloc[0]['move_rate']) * n_agents
            if not math.isclose(len(annual), expected, rel_tol=0, abs_tol=1e-7):
                raise ValueError('Accepted move count disagrees with history; check record_events=True.')
            events = []
            for event in annual.to_dict('records'):
                origin, destination = event['origin'], event['destination']
                if origin not in states or destination not in states or origin == destination:
                    raise ValueError('Move endpoints must be different modeled states.')
                chain = int(event.get('chain_move', 0))
                if chain not in (0, 1):
                    raise ValueError('chain_move must be zero or one.')
                events.append([origin, destination, chain])
            for state in states:
                if (sum(e[0] == state for e in events) != int(indexed.loc[state, 'outflow'])
                        or sum(e[1] == state for e in events) != int(indexed.loc[state, 'inflow'])):
                    raise ValueError('Move routes disagree with state inflow/outflow totals.')
            frames.append({'year':year, 'population':population, 'moves':events,
                           'housing_rejection':float(rows.iloc[0].get('housing_rejection_rate', 0))})
        scenarios.append({'name':str(run['name']), 'n_agents':n_agents, 'frames':frames})
    if not scenarios:
        raise ValueError('At least one scenario is required.')
    return MigrationAnimation({'states':locations, 'target':target_state,
                               'seed':int(seed), 'scenarios':scenarios})


def make_comparison(namespace, *, n_agents=600, years=12, seed=201):
    """Run baseline and intensity-1 combined policy at the same seed.

    Uses the notebook's cross_policy and PolicySocialABM verbatim. Models copy
    their inputs; no existing model, parameters, global target or RNG is changed.
    """
    for name, value, minimum in [('n_agents',n_agents,2), ('years',years,1), ('seed',seed,0)]:
        if not isinstance(value, Integral) or isinstance(value, bool) or value < minimum:
            raise ValueError(f'{name} must be an integer >= {minimum}.')
    runs = []
    for policy, label in [('baseline','No policy'), ('combined','Combined policy · intensity 1')]:
        model = namespace['PolicySocialABM'](
            namespace['state_data'], namespace['cross_policy'](policy, 1.0),
            n_agents=n_agents, years=years, seed=seed,
            params=namespace['PARAMS'].copy(), interaction_strength=1.0, record_events=True)
        history, moves, _ = model.run()
        runs.append({'name':label, 'history':history, 'moves':moves, 'n_agents':n_agents})
    return from_runs(runs, namespace['STATE_COORDS'], target_state=namespace['FOCAL_STATE'], seed=seed)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('migration_animation.html'))
    parser.add_argument('--agents', type=int, default=600)
    parser.add_argument('--years', type=int, default=12)
    parser.add_argument('--seed', type=int, default=201)
    return parser


def parse_args(argv=None):
    """Parse and validate command-line arguments before any model is loaded."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.agents < 2:
        parser.error('--agents must be at least 2')
    if args.years < 1:
        parser.error('--years must be at least 1')
    if args.seed < 0:
        parser.error('--seed must not be negative')
    if args.output.suffix.lower() not in ('.html', '.htm'):
        parser.error('--output must end in .html or .htm')
    if not args.output.resolve().parent.is_dir():
        parser.error(f'--output directory does not exist: {args.output.resolve().parent}')
    return args


def main(argv=None):
    args = parse_args(argv)
    from rebuild_scripts.v8lib import load
    namespace = load(Path(__file__).with_name('0914-1_v8.ipynb'))
    animation = make_comparison(namespace, n_agents=args.agents, years=args.years, seed=args.seed)
    print('Saved', animation.save(args.output).resolve())


if __name__ == '__main__':
    main()
