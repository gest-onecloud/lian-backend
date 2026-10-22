"""Leakage-safe current domestic competition registry for cross-competition fixtures.

This registry is metadata, not match outcome data. It is only used for fixtures on/after
its effective_from date. Unknown teams remain unknown rather than being guessed.
"""
REGISTRY = {
    # England 2026/27 teams appearing in the local Carabao sample.
    'birmingham city': {'league':'Championship','tier':4,'effective_from':'2026-07-01'},
    'blackburn rovers': {'league':'Championship','tier':4,'effective_from':'2026-07-01'},
    'middlesbrough': {'league':'Championship','tier':4,'effective_from':'2026-07-01'},
    'millwall': {'league':'Championship','tier':4,'effective_from':'2026-07-01'},
    'norwich city': {'league':'Championship','tier':4,'effective_from':'2026-07-01'},
    'southampton': {'league':'Championship','tier':4,'effective_from':'2026-07-01'},
    'stoke city': {'league':'Championship','tier':4,'effective_from':'2026-07-01'},
    'hull city': {'league':'Championship','tier':4,'effective_from':'2026-07-01'},
    'watford': {'league':'Championship','tier':4,'effective_from':'2026-07-01'},
    'sheffield united': {'league':'Championship','tier':4,'effective_from':'2026-07-01'},
    'ipswich town': {'league':'Premier League','tier':5,'effective_from':'2026-07-01'},
    'leicester city': {'league':'League One','tier':3,'effective_from':'2026-07-01'},
    'coventry city': {'league':'Premier League','tier':5,'effective_from':'2026-07-01'},
    'sheffield wednesday': {'league':'League One','tier':3,'effective_from':'2026-07-01'},
    'doncaster rovers': {'league':'League One','tier':3,'effective_from':'2026-07-01'},
    'barnsley': {'league':'League One','tier':3,'effective_from':'2026-07-01'},
    'crewe alexandra': {'league':'League Two','tier':2,'effective_from':'2026-07-01'},
    'peterborough united': {'league':'League One','tier':3,'effective_from':'2026-07-01'},
    'blackpool': {'league':'League One','tier':3,'effective_from':'2026-07-01'},
    'lincoln city': {'league':'League One','tier':3,'effective_from':'2026-07-01'},
    'leyton orient': {'league':'League One','tier':3,'effective_from':'2026-07-01'},
    'cambridge united': {'league':'League One','tier':3,'effective_from':'2026-07-01'},
    'fleetwood town': {'league':'League Two','tier':2,'effective_from':'2026-07-01'},
    'shrewsbury town': {'league':'League Two','tier':2,'effective_from':'2026-07-01'},
}
