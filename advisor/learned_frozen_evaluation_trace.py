"""Frozen evaluation traces reused from the accepted Q_dev_new owner."""
from copy import deepcopy
from collections import Counter
import json, os
import numpy as np
from advisor.learned_execution_alignment import content_hash, digest, durable_json
from scripts.pilot_foundation_selfplay_exploration import FrozenEvalCases

def append(stream, row):
    stream.write(json.dumps(row, allow_nan=False, ensure_ascii=False) + '\n')

class Trace:
    def __init__(self,root):
        self.root=root;self.stream=None;self.finished={};self.current=None
    def begin(self,model,seat,index):
        if self.stream is not None:raise ValueError('previous_trace_not_committed')
        self.model,self.seat,self.index=model,seat,index
        self.key=f'{model}_league_s0_{seat}_{index}'
        self.path=self.root/'decisions'/(self.key+'.jsonl')
        self.stream=self.path.open('x',encoding='utf-8');self.counts=Counter();self.first=None;self.last={};self.steps=0
        from advisor.learned_difficulty_calibration import PublicRetryAudit
        self.retry=PublicRetryAudit(self.key)
    def infer(self,name,actor,original,view):
        from advisor.learned_response_predictor import public_input
        from advisor.learned_tactical_diagnostics import action_class
        public=public_input(view);proof=original(view);action=int(proof['action_index'])
        role='candidate' if view['side']==('self' if self.seat=='p1' else 'opponent') else 'rival'
        if name!=(self.model if role=='candidate' else 'Foundation'):raise ValueError('trace_policy_owner_mismatch')
        probabilities=np.asarray(proof['action_probabilities'])
        if not view['action_mask'][action] or int(probabilities.argmax())!=action or not np.isfinite(probabilities).all():
            raise ValueError('trace_nonargmax_or_illegal_action')
        row={'phase':'selected_before_native_step','role':role,'model':name,'model_SHA256':actor.model_id,
             'case':self.index,'seat':self.seat,'ordinal':self.counts[role],'episode_id':view['episode_id'],'revision':view['revision'],
             'public_input_SHA256':content_hash(public),'action':action,'native_choice':view['choices'][action],
             'mask':view['action_mask'],'probabilities':proof['action_probabilities'],'value':proof['discounted_return_estimate'],
             'family':action_class(view,action)}
        if role=='candidate' and self.first is None:
            row['feature_SHA256']=__import__('hashlib').sha256(np.asarray(actor.encoder.encode(view)).tobytes()).hexdigest()
            initial=self.root/'initial_public'/(self.key+'.json')
            durable_json(initial,{'view':view,'proof':row,'public_scope':'authenticated own view; no simulator truth'})
            self.first=deepcopy(row);self.initial_path=initial
        append(self.stream,row);self.counts[role]+=1;self.last[view['side']]=row
        return proof
    def observe(self,event):
        for side,action in event['actions'].items():
            if self.last[side]['action']!=action or self.last[side]['revision']!=event['before'][side]['revision']:
                raise ValueError('trace_native_selection_binding')
        append(self.stream,{'phase':'native_result','ordinal':self.steps,'actions':event['actions'],'result':event['result']})
        self.steps+=1
        self.retry.observe(event)
        if event['result']['action_rejected']:
            self.stream.flush();os.fsync(self.stream.fileno());raise ValueError('native_rejection_no_replacement')
    def finish(self,record):
        if self.counts['candidate']!=record['decisions'] or self.counts['rival']!=record['decisions'] or self.steps!=record['decisions']:
            raise ValueError('trace_decision_count')
        self.stream.flush();os.fsync(self.stream.fileno());self.stream.close();self.stream=None
        receipt={'trace_path':str(self.path),'trace_SHA256':digest(self.path),'initial_public_path':str(self.initial_path),
                 'initial_public_SHA256':digest(self.initial_path),'first':self.first,'decisions':record['decisions'],
                 'record_SHA256':content_hash(record),'key':self.key}
        durable_json(self.root/'trace_receipts'/(self.key+'.json'),receipt)
        self.finished[self.index]=receipt
    def close(self):
        if self.stream is not None:self.stream.flush();os.fsync(self.stream.fileno());self.stream.close();self.stream=None

class Provider(FrozenEvalCases):
    def __init__(self,*args,trace,**kwargs):super().__init__(*args,**kwargs);self.trace=trace
    def __call__(self,split,index):
        case=super().__call__(split,index);self.trace.begin(self.policy,self.seat,index);return case
