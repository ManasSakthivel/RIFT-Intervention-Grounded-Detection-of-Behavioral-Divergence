import sys, warnings, io, contextlib
warnings.filterwarnings("ignore")
sys.path.insert(0, "."); sys.path.insert(0, "src")
import numpy as np, pandas as pd
from causallearn.search.ConstraintBased.FCI import fci
from causallearn.utils.cit import fisherz
from src.rift.fci.fci_runner import _decode_pag_edges
from src.rift.ebd.ebd import _pag_to_digraph
from src.rift.fci.fci_runner import PAGResult
rng=np.random.default_rng(1); n=800
X=rng.normal(size=n);Y=rng.normal(size=n);Z=X+Y+0.5*rng.normal(size=n)
with contextlib.redirect_stdout(io.StringIO()):
    g,_=fci(np.c_[X,Y,Z],fisherz,0.05,verbose=False,show_progress=False)
print(g.graph.astype(int).tolist())
e,_=_decode_pag_edges(g.graph,["X","Y","Z"])
print([(x.source,x.target,x.edge_type.value) for x in e])
d=_pag_to_digraph(PAGResult(variables=["X","Y","Z"],edges=e))
print("Z->X reachable in EBD graph:",d.has_edge("Z","X"))
