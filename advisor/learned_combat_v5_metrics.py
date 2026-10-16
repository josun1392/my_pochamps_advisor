"""Loss-only held-out prediction scoring, never a policy observation producer."""
import numpy as np
import torch
from advisor.learned_combat_v5_aux import supervision_targets
from advisor.learned_combat_v5 import FAMILIES


class V5PredictionMetrics:
    def __init__(self):
        self.rows=0
        self.categorical={k:{"n":0,"correct":0,"nll_sum":0.,"brier_sum":0.,"out_of_public_support":0,
            "bins":[[0,0.,0.] for _ in range(10)],"classes":{}} for k in ("action","abilities","items")}
        self.moves={"rows":0,"unknown_cells":0,"positive_cells":0,"bce_sum":0.,"brier_sum":0.,
                    "top4_hits":0,"out_of_public_support":0}

    def observe(self,player,before,opponent_before,after):
        y=supervision_targets(before,opponent_before,after["public_history"][len(before["public_history"]):],player.encoder)
        x=torch.tensor(player.encoder.encode(before))[None]
        with torch.no_grad():logits,support,_,known_moves=player.model.policy.opponent_predictions(x)
        self.rows+=1
        for kind in self.categorical:
            target=y[kind]
            # Do not let already revealed values inflate hidden prediction scores.
            if target<0 or kind!="action" and not y["unknown_"+kind]:continue
            row=self.categorical[kind];z=logits[kind][0]
            if kind!="action":
                if not support[kind][0,target]:row["out_of_public_support"]+=1;continue
                z=z.masked_fill(~support[kind][0].bool(),-1e8)
            p=z.softmax(0).cpu().numpy();correct=int(p.argmax()==target);confidence=float(p.max())
            row['n']+=1;row['correct']+=correct;row['nll_sum']+=float(-np.log(max(float(p[target]),1e-8)))
            row['brier_sum']+=float((p*p).sum()-2*p[target]+1)
            b=row['bins'][min(9,int(confidence*10))];b[0]+=1;b[1]+=confidence;b[2]+=correct
            name=FAMILIES[target] if kind=='action' else str(target)
            row['classes'][name]=row['classes'].get(name,0)+1
        if y['moves_complete']:
            mask=support['moves'][0].cpu().numpy().astype(bool)
            truth=np.zeros_like(mask,dtype=float)
            truth[[t for t in y['moves'] if t>0]]=1
            if np.any(truth[~mask]):self.moves['out_of_public_support']+=1;return
            mask &= ~known_moves[0].cpu().numpy().astype(bool)
            p=logits['moves'][0].sigmoid().cpu().numpy().astype(float);q=np.clip(p,1e-8,1-1e-8)
            m=self.moves;m['rows']+=1;m['unknown_cells']+=int(mask.sum());m['positive_cells']+=int(truth[mask].sum())
            m['bce_sum']+=float((-truth[mask]*np.log(q[mask])-(1-truth[mask])*np.log(1-q[mask])).sum())
            m['brier_sum']+=float(((p[mask]-truth[mask])**2).sum())
            top=np.argsort(np.where(mask,p,-1))[-min(4,int(mask.sum())):] if mask.any() else []
            m['top4_hits']+=int(truth[top].sum())

    def result(self):
        return {'schema_version':'showdown-v5-heldout-prediction-metrics-v1','sampled_public_decisions':self.rows,
                'scope':'first_up_to_8_nonwait_decisions_per_battle_unknown_fields_only_not_training_accuracy',
                'categorical':self.categorical,'moves':self.moves}
