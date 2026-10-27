"""No native execution or optimizer updates: reciprocal case/statistical contracts."""
from copy import deepcopy
import pytest
from scripts.pilot_foundation_balanced_micro import frozen_cases,gate,paired
from advisor.learned_fixed_micro import FixedMicroCases
from advisor.learned_selfplay_pilot import OPPONENTS


def templates():
    out=[]
    for pair in range(6):
        for d in (0,1):
            scope='train'if pair<2 else'development'if pair<4 else'independent'
            out.append({'pair':pair,'direction':d,'scope':scope,'scenario':{
                'teams':{'self':[pair,d],'opponent':[pair,1-d]},
                'preview':{'self':[1,2,3],'opponent':[3,2,1]},'seed':[]}})
    return out


def rows(cases,models=('Foundation',)):
    return [{'policy':m,'case':c['index'],'seat':s,'record':{'winner':'self'if c['replicate']%2 else'opponent',
        'truncated':False,'tactical_counts':{'available:attack':2,'available:switch':2,'available:setup':1}}}
        for m in models for c in cases for s in ('p1','p2')]


def test_phase_seeds_teams_and_both_ownership_directions():
    ts=templates();phases=[frozen_cases(ts,p)for p in ('development','precheck','final')]
    assert all(len(cs)==64 for cs in phases)
    assert {c['pair']for c in phases[0]}=={2,3}
    assert {c['pair']for c in phases[1]}=={4,5}
    assert {c['pair']for c in phases[2]}=={0,1,4,5}
    seeds=[{tuple(c['scenario']['seed'])for c in cs}for cs in phases]
    assert not seeds[0]&seeds[1]and not seeds[1]&seeds[2]
    for cs in phases:
        for c in cs:
            other=next(x for x in cs if (x['pair'],x['rival'],x['replicate'],x['direction'])==
                (c['pair'],c['rival'],c['replicate'],1-c['direction']))
            assert other['scenario']['seed']==c['scenario']['seed']
            assert other['scenario']['teams']['self']==c['scenario']['teams']['opponent']


def test_train_template_cycle_does_not_confuse_rival_with_direction():
    p={'schema_version':'new_version','seed':104028,'templates':templates(),'training_template_indices':[0,1,2,3]}
    sampler=FixedMicroCases(p)
    for i in range(16):
        assert sampler('train',i)['teams']==p['templates'][i//4]['scenario']['teams']
        assert sampler('train',i)['scenario_id'].startswith('new_version:TRAIN:')
    assert {OPPONENTS[i%4]for i in range(4)}==set(OPPONENTS)


def test_design_gate_balanced_pass_and_directional_saturation_fails():
    cs=frozen_cases(templates(),'development');rs=rows(cs)
    assert gate(rs,cs)['passed']
    for r in rs:r['record']['winner']='self'if cs[r['case']]['direction']==0 else'opponent'
    result=gate(rs,cs)
    assert result['winrate']==.5 and not result['passed']
    assert result['directions']=={0:1.,1:0.}


def test_no_opportunities_no_go_and_no_receipt_substitution():
    cs=frozen_cases(templates(),'precheck');rs=rows(cs)
    for r in rs:r['record']['tactical_counts']={}
    assert not gate(rs,cs)['passed']
    rs[-1]=deepcopy(rs[0])
    with pytest.raises(ValueError):gate(rs,cs)


def test_final_bootstrap_clusters_both_team_directions_and_seats():
    cs=frozen_cases(templates(),'final');rs=rows(cs,('Foundation','Micro'))
    result=paired(rs,cs,draws=1000)
    assert result['independent']['clusters']==16
    assert result['independent']['games_per_model']==64
    assert result['independent']['conditional_cluster_95CI']==[0.,0.]
    assert result['verdict']=='MICRO_INCONCLUSIVE'
    with pytest.raises(ValueError):paired(rs[:-1],cs,draws=10)


def test_pair_specific_saturation_is_not_hidden_by_balanced_overall_average():
    cs=frozen_cases(templates(),'precheck');rs=rows(cs)
    for r in rs:
        c=cs[r['case']]
        if c['pair']==5:r['record']['winner']='self'if c['direction']else'opponent'
    result=gate(rs,cs)
    assert result['winrate']==.5
    assert result['directions']=={0:.25,1:.75}
    assert not result['passed']
