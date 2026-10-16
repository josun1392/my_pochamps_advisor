"""Build small public-support priors from a verified TRAIN-only native subset.

No validation/test sets or real opposing runtime sets are read by inference.
The optional executed-action frequencies must come from separate train episodes.
"""
import argparse,json,hashlib,subprocess,sys
from pathlib import Path
from collections import Counter,defaultdict
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from advisor.learned_training_subset import NativeTrainingSubset
from advisor.learned_encoder import identifier,fingerprint
from advisor.showdown_bridge import SHOWDOWN_COMMIT,FORMAT_ID

def build(checkout,subset_path,subset_sha,frequencies):
    if subprocess.check_output(['git','-C',str(checkout),'rev-parse','HEAD'],text=True).strip()!=SHOWDOWN_COMMIT:raise ValueError('unpinned_prior_source')
    subset=NativeTrainingSubset(subset_path,subset_sha)
    if frequencies['schema_version']!='showdown-public-executed-action-frequency-v1' or frequencies['training_subset_sha256']!=subset_sha:raise ValueError('train_only_frequency_binding_required')
    species={};global_counts={k:Counter() for k in ('abilities','items','moves')}
    for team in subset.teams:
        for p in team:
            row=species.setdefault(identifier(p['species']),{'sets':0,'abilities':Counter(),'items':Counter(),'moves':Counter()});row['sets']+=1
            for kind,values in (('abilities',[p['ability']]),('items',[p.get('item','')]),('moves',set(p['moves']))):
                for value in values:row[kind][identifier(value)]+=1;global_counts[kind][identifier(value)]+=1
    # Read native callback presence, never implement callbacks in Python.
    source="""const path=require('path');const {Dex}=require(path.join(process.argv[1],'dist','sim'));const d=Dex.forFormat(process.argv[2]);
    const rows={};for(const m of d.moves.all()){rows[m.id]={type:m.type,category:m.category,power:m.basePower,priority:m.priority,flags:m.flags,
    referenceSupported:m.basePower>0&&['Physical','Special'].includes(m.category)&&!m.multihit&&!m.ohko&&!m.damage&&!m.damageCallback&&!m.basePowerCallback&&!m.onBasePower&&!m.onModifyMove&&!m.onModifyType&&!m.onTry&&!m.onTryHit&&!m.onHit&&!m.overrideOffensiveStat&&!m.overrideDefensiveStat&&!m.useSourceDefensiveAsOffensive&&!m.useTargetOffensive&&!m.willCrit};}process.stdout.write(JSON.stringify(rows));"""
    moves=json.loads(subprocess.check_output(['node','-e',source,str(checkout),FORMAT_ID],text=True))
    result={'schema_version':'showdown-public-combat-priors-v3','engine_commit':SHOWDOWN_COMMIT,'format_id':FORMAT_ID,
      'training_subset_sha256':subset_sha,'training_teams':len(subset.teams),'species':species,'global_counts':global_counts,
      'executed_action_counts':frequencies['counts'],'action_frequency_source_sha256':fingerprint(frequencies),
      'native_moves':moves,'native_query_sha256':hashlib.sha256(source.encode()).hexdigest(),
      'smoothing':{'species_pseudocount':16,'global_uniform_mixture':.5,'action_frequency_pseudocount':1},
      'scope':'public_prior_not_actual_hidden_set_or_competitive_usage; full train-only provenance'}
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument('--checkout',required=True);p.add_argument('--subset',required=True);p.add_argument('--subset-sha256',required=True);p.add_argument('--frequencies',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    result=build(a.checkout,a.subset,a.subset_sha256,json.loads(Path(a.frequencies).read_text()));out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():raise ValueError('do_not_overwrite_prior_identity')
    out.write_text(json.dumps(result,sort_keys=True,separators=(',',':')),encoding='utf-8');print(json.dumps({'path':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'species':len(result['species']),'reference_moves':sum(m['referenceSupported'] for m in result['native_moves'].values())}))
if __name__=='__main__':main()
