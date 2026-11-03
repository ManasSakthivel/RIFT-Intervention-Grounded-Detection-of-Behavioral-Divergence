import json, subprocess, hashlib, sys
m=json.load(open('artifacts/sprint4_5_0/prereg/freeze_manifest.json'))
files=m['files']
items=files.items() if isinstance(files,dict) else [(f.get('path'),f) for f in files]
res=[];bad=[]
for p,v in items:
    exp=v if isinstance(v,str) else (v.get('sha256') if isinstance(v,dict) else None)
    wt=hashlib.sha256(open(p,'rb').read()).hexdigest()
    head=hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+p])).hexdigest()
    ok=(wt==exp==head)
    res.append(dict(path=p,manifest=exp,worktree=wt,head=head,ok=ok))
    if not ok: bad.append(p)
json.dump(dict(n=len(res),mismatches=bad,results=res),open('artifacts/sprint4_5_1/repro/manifest_verification.json','w'),indent=1)
print(len(res),'files; mismatches:',bad)
