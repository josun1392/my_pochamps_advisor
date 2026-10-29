"""Execute only the frozen lambda-one versus historical lambda-.95 study."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from advisor import learned_gae_study
from scripts.run_foundation_parent_anchor_study import main

if __name__ == '__main__':
    main(study=learned_gae_study)
