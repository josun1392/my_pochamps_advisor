"""Run the frozen residual-only study with the maintained detached native owner."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from advisor import learned_legal_set_study
from scripts.run_foundation_parent_anchor_study import main

if __name__=='__main__':
    main(study=learned_legal_set_study)
