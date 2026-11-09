import sys, json, warnings, importlib.util
warnings.filterwarnings("ignore")
sys.path.insert(0, "."); sys.path.insert(0, "src")
spec=importlib.util.spec_from_file_location("rre","scripts/run_reproducible_evaluation.py"); rre=importlib.util.module_from_spec(spec); spec.loader.exec_module(rre)
from rift.ebd.ebd import compute_ebd
val=json.load(open("datasets/rift_faults/validation.json"))["scenarios"]
sc=[s for s in val if s["fault_id"]=="DF_02"][0]
svc=rre.SyntheticBenchmark.SERVICES
m=rre.generate_scenario_metrics(sc,svc,10.0,sc["seed"])
print("DF_02 mean(value) after t>=60 per svc:", {s:round(float(m[s][m[s]['time']>=60]['value'].mean()),1) for s in ("product_catalog","recommendation","frontend")})
pag=rre.build_oracle_pag(sc)
res=compute_ebd(m,{s:{"mean":0.0,"std":10.0} for s in svc},pag,(0.0,180.0))
print([(r.service_id,r.confidence,r.r2_pass,r.r3_pass,[tuple(e) for e in r.causal_path]) for r in res if r.r1_pass])
# incident_window derived from ground-truth injected_at_t:
print("injected_at_t in scenario used for incident_window:", sc["injected_at_t"])
