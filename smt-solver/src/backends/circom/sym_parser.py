"""
Parser for Circom .sym (symbol) files.

The .sym file format maps signal names to wire indices:
    <label_id>,<wire_index>,<component_index>,<signal_name>

Example:
    1,1,0,main.out
    2,2,0,main.arr[0]
    3,3,0,main.arr[1]
    4,4,0,main.flag
"""

from pathlib import Path
from typing import Dict, Set


def parse_sym_file(sym_path: Path) -> Dict[str, int]:
    """
    Parse a Circom .sym file and return a mapping from signal names to wire indices.
    
    Args:
        sym_path: Path to the .sym file
        
    Returns:
        Dictionary mapping signal_name -> wire_index
        Example: {"main.a": 2, "main.b": 3, "main.c": 1}
    """
    signal_to_wire: Dict[str, int] = {}
    
    with open(sym_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            parts = line.split(',')
            if len(parts) != 4:
                continue  # Skip malformed lines
            
            label_id, wire_index, component_index, signal_name = parts
            
            try:
                wire_idx = int(wire_index)
                signal_to_wire[signal_name] = wire_idx
            except ValueError:
                # Skip lines with non-numeric wire index
                continue
    
    return signal_to_wire


def resolve_bool_wires(sym_path: Path, signal_names: list[str]) -> Set[int]:
    """
    Given a .sym file and a list of signal names, return the set of wire indices
    that correspond to those signals.
    
    Args:
        sym_path: Path to the .sym file
        signal_names: List of signal names to mark as boolean (e.g., ["main.flag", "main.arr[0]"])
        
    Returns:
        Set of wire indices that should be treated as boolean
        
    Raises:
        ValueError: If any signal name is not found in the .sym file
    """
    signal_to_wire = parse_sym_file(sym_path)
    bool_wire_indices: Set[int] = set()
    
    for signal_name in signal_names:
        if signal_name not in signal_to_wire:
            available = ", ".join(sorted(signal_to_wire.keys())[:10])
            raise ValueError(
                f"Signal '{signal_name}' not found in .sym file. "
                f"Available signals: {available}..."
            )
        bool_wire_indices.add(signal_to_wire[signal_name])
    
    return bool_wire_indices
