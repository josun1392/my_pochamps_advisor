"""Frozen preserved-TRAIN public native teacher gate. Never launches PPO/eval."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
from collections import Counter
from hashlib import sha256
import json
from time import perf_counter
from advisor.learned_public_native_teacher import PublicNativeTeacher, VERSION
from advisor.learned_action_search_teacher import validate_public_teacher_target
from advisor.learning_resources import atomic_json


def audit(config, output):
    if output.exists():raise ValueError("existing_native_teacher_receipt_do_not_duplicate")
    source=Path(config["public_decisions"])
    payload=source.read_bytes()
    if (config.get("schema_version")!="bounded-public-native-teacher-plan-v1"
            or config.get("rows")!=512 or config.get("selection")!="all_public_before_file_order"
            or sha256(payload).hexdigest()!=config["public_decisions_SHA256"]):
        raise ValueError("frozen_public_teacher_source_contract_mismatch")
    views=[json.loads(line)["public_before"]for line in payload.decode("utf-8").splitlines()]
    if len(views)!=512:raise ValueError("public_teacher_expected_512_rows")
    teacher=PublicNativeTeacher(checkout=config["checkout"],catalog=config["catalog"],ledger_path=config["ledger"])
    reasons=Counter();rows=[];seen=set();started=perf_counter()
    for view in views:
        key=(view["episode_id"],view["revision"],view["side"])
        if key in seen:raise ValueError("duplicate_public_teacher_decision")
        seen.add(key)
        decision=teacher.assess(view,policy_id=config["policy_id"],learning_step=config["learning_step"])
        target=validate_public_teacher_target(decision,view,policy_id=config["policy_id"],learning_step=config["learning_step"])
        reasons[decision.get("reason","supported")]+=1
        rows.append({"binding":decision["binding"],"supported":target is not None,
            "reason":decision.get("reason"),"native_evidence":decision.get("native_evidence")})
    supported=sum(r["supported"]for r in rows)
    result={"provider_version":VERSION,"actual_preserved_TRAIN_decisions":512,"approved_targets":supported,
        "abstained":512-supported,"reasons":dict(reasons),"rows":rows,
        "independent_mini_gate":{"minimum_decisions":16,"minimum_situation_families":2,
            "supported_situation_families":int(supported>0),"passed":False},
        "status":"PUBLIC_TEACHER_NOT_VIABLE_IN_BOUNDED_SCOPE"if supported<16 else"MICRO_GATE_NOT_ESTABLISHED",
        "new_PPO_transitions":0,"new_Adam_steps":0,"new_independent_evaluations":0,
        "wall_seconds":perf_counter()-started,"source_SHA256":config["public_decisions_SHA256"]}
    atomic_json(output,result)
    print(json.dumps({k:v for k,v in result.items()if k!='rows'}),flush=True)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();audit(json.loads(a.plan.read_text(encoding='utf-8')),a.output)


if __name__=='__main__':main()
