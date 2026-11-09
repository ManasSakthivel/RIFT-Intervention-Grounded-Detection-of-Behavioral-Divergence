import sys, json, warnings, importlib.util
warnings.filterwarnings("ignore")
sys.path.insert(0, "."); sys.path.insert(0, "src"); sys.path.insert(0,"scripts")
spec=importlib.util.spec_from_file_location("rre","scripts/run_reproducible_evaluation.py"); rre=importlib.util.module_from_spec(spec); spec.loader.exec_module(rre)
from rift.baselines import IncidentContext
dev=json.load(open("datasets/rift_faults/development.json"))["scenarios"]
svc=rre.SyntheticBenchmark.SERVICES; cg=rre.build_call_graph()
bs={s:{"mean":0.0,"std":10.0} for s in svc}
def ctx(sc):
    m=rre.generate_scenario_metrics(sc,svc,10.0,sc.get("seed",42)); ia=sc.get("injected_at_t",60.0)
    return IncidentContext(fault_id=sc["fault_id"],incident_window=(max(0,ia-60),ia+120),metrics=m,baseline_stats=bs,call_graph=cg,scenario_seed=sc.get("seed",42))
from collections import Counter
for label,flag in (("confounded",True),("non-confounded",False)):
    cnt=Counter()
    for sc in [s for s in dev if s["confounded"]==flag]:
        o=rre.run_rift_full_scenario(sc,ctx(sc),use_oracle_pag=True)
        cnt[("ABSTAIN:"+str(o.abstention_reason)) if o.abstained else ("ATTR_OK" if o.top_candidates[0][0]==sc["root_cause_service"] else "ATTR_WRONG")]+=1
    print("ORACLE-PAG",label,dict(cnt))
# learned
for label,flag in (("confounded",True),("non-confounded",False)):
    cnt=Counter()
    for sc in [s for s in dev if s["confounded"]==flag]:
        o=rre.run_rift_full_scenario(sc,ctx(sc),use_oracle_pag=False)
        cnt[("ABSTAIN:"+str(o.abstention_reason)) if o.abstained else ("ATTR_OK" if o.top_candidates[0][0]==sc["root_cause_service"] else "ATTR_WRONG")]+=1
    print("LEARNED(all)",label,dict(cnt))
