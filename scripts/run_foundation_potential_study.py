"""Execute only a pre-frozen public-potential matched study."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_foundation_parent_anchor_study import main
from advisor import learned_potential_study
if __name__ == "__main__":
    main(study=learned_potential_study)
