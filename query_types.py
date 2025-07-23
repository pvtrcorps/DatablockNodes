"""Defines the data structures for selection queries."""
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class FNSelectionQuery:
    """A compiled representation of a selection expression."""
    raw_expression: str
    path_glob: str
    filters: List[Dict[str, Any]] = field(default_factory=list)
