"""Existing detached study owner, two-group-only matching and frozen evaluation."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from advisor import learned_two_group_study
from scripts.run_foundation_parent_anchor_study import main

if __name__ == "__main__":
    main(study=learned_two_group_study)
