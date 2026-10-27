"""Local oral-script matrix expander and text gate (v0.1)."""

__version__ = "0.1.0"

from touliu_script_matrix.atoms import AtomsError, load_atoms
from touliu_script_matrix.expand import expand
from touliu_script_matrix.gates import evaluate

__all__ = [
    "AtomsError",
    "__version__",
    "evaluate",
    "expand",
    "load_atoms",
]
