"""
SMT formula pruning: Reduce n variables to k by substituting (n-k) variables with:
- Model values (if SAT) - preserves SAT
- Random booleans (if UNSAT) - preserves UNSAT by contradiction
"""

import random
from typing import Dict, List, Set, Tuple, Optional, Any
from io import StringIO


def run_smt_solver(smtlib2_str: str, solver: str = "z3") -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Public wrapper for running SMT solver. Used by tests.
    
    Args:
        smtlib2_str: SMT-LIB v2 formula as string
        solver: Solver to use ("z3" or "cvc5")
    
    Returns:
        Tuple of (result, model) where:
        - result: "sat", "unsat", or "unknown"
        - model: Dictionary mapping variable names to values (if SAT), None otherwise
    """
    if solver == "cvc5":
        # ------------------------------------------------------------------
        # THIS IMPORT NEEDS TO STAY TO AVOID PROBLEMS BETWEEN PYSMT AND CVC5
        import cvc5.pythonic
        # ------------------------------------------------------------------
    
    from pysmt.shortcuts import Solver, Symbol, And, TRUE, FALSE, Int
    from pysmt.smtlib.parser import SmtLibParser
    from pysmt.exceptions import SolverReturnedUnknownResultError
    
    def _add_fused_variable_constraints(smtlib2_str: str) -> str:
        """
        Add temporary XOR constraints for fused variables to ensure consistent model values.
        """
        import re
        FUSION_SUFFIX = "_fused"
        
        fused_pattern = re.compile(r'\(declare-fun (\w+' + re.escape(FUSION_SUFFIX) + r') \(\) Bool\)')
        fused_vars = fused_pattern.findall(smtlib2_str)
        
        if not fused_vars:
            return smtlib2_str
        
        constraints = []
        for fused_var in fused_vars:
            base = fused_var[:-len(FUSION_SUFFIX)]
            first = base.find("scr")
            if first == -1:
                continue
            second = base.find("scr", first + 1)
            if second == -1:
                continue
            
            var1 = base[:second]
            if var1.endswith("_"):
                var1 = var1[:-1]
            var2 = base[second:]
            
            constraints.append(f"(assert (= {fused_var} (xor {var1} {var2})))")
        
        lines = smtlib2_str.split('\n')
        insert_idx = len(lines)
        for i, line in enumerate(lines):
            if line.strip().startswith('(check-sat'):
                insert_idx = i
                break
        
        for constraint in constraints:
            lines.insert(insert_idx, constraint)
            insert_idx += 1
        
        return '\n'.join(lines)
    
    try:
        smtlib2_str_with_constraints = _add_fused_variable_constraints(smtlib2_str)
        
        parser = SmtLibParser()
        script = parser.get_script(StringIO(smtlib2_str_with_constraints))
        
        assertions = []
        for cmd in script.commands:
            if cmd.name == "assert":
                assertions.append(cmd.args[0])
        
        if not assertions:
            return "sat", {}
        
        formula = And(assertions) if len(assertions) > 1 else assertions[0]
        
        with Solver(name=solver) as s:
            s.add_assertion(formula)
            result = s.solve()
            
            if result:
                model = s.get_model()
                model_dict = {}
                
                for var_symbol in formula.get_free_variables():
                    var_name = var_symbol.symbol_name()
                    if var_name == "div":
                        continue
                    
                    if var_symbol in model:
                        value = model[var_symbol]
                        if value.is_bool_constant():
                            model_dict[var_name] = value.is_true()
                        elif value.is_int_constant():
                            model_dict[var_name] = value.constant_value()
                        else:
                            model_dict[var_name] = str(value)
                
                return "sat", model_dict
            else:
                return "unsat", None
                
    except SolverReturnedUnknownResultError:
        return "unknown", None
    except Exception as e:
        import traceback
        traceback.print_exc()
        return "unknown", None


def prune_formula(
    smtlib2_str: str, 
    k: int, 
    solver: str = "z3", 
    seed: Optional[int] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Prune an SMT formula to k variables.
    
    Args:
        smtlib2_str: SMT-LIB v2 formula as string
        k: Number of variables to keep
        solver: Solver to use ("z3" or "cvc5")
        seed: Random seed for reproducibility
    
    Returns:
        Tuple of (pruned_smtlib, metadata) where:
        - pruned_smtlib: Modified SMT-LIB string
        - metadata: Dictionary with pruning information
    """
    if solver == "cvc5":
        # ------------------------------------------------------------------
        # THIS IMPORT NEEDS TO STAY TO AVOID PROBLEMS BETWEEN PYSMT AND CVC5
        import cvc5.pythonic
        # ------------------------------------------------------------------
    
    from pysmt.shortcuts import Solver, Symbol, And, TRUE, FALSE, Int, substitute
    from pysmt.smtlib.parser import SmtLibParser
    from pysmt.smtlib.script import SmtLibCommand
    from pysmt.exceptions import SolverReturnedUnknownResultError
    from pysmt.typing import BOOL
    
    def _add_fused_variable_constraints(smtlib2_str: str) -> str:
        """
        Add temporary XOR constraints for fused variables to ensure consistent model values.
        These constraints are only for getting the model during pruning and should not
        appear in the final pruned formula.
        
        Args:
            smtlib2_str: SMT-LIB v2 formula as string
        
        Returns:
            Formula with added XOR constraints for fused variables
        """
        import re
        FUSION_SUFFIX = "_fused"
        
        # Find all fused variable declarations
        fused_pattern = re.compile(r'\(declare-fun (\w+' + re.escape(FUSION_SUFFIX) + r') \(\) Bool\)')
        fused_vars = fused_pattern.findall(smtlib2_str)
        
        if not fused_vars:
            return smtlib2_str
        
        # Build XOR constraints for each fused variable
        constraints = []
        for fused_var in fused_vars:
            base = fused_var[:-len(FUSION_SUFFIX)]
            
            # Find component variable names
            first = base.find("scr")
            if first == -1:
                continue
            second = base.find("scr", first + 1)
            if second == -1:
                continue
            
            var1 = base[:second]
            if var1.endswith("_"):
                var1 = var1[:-1]
            var2 = base[second:]
            
            # Add constraint: fused_var = xor(var1, var2)
            constraints.append(f"(assert (= {fused_var} (xor {var1} {var2})))")
        
        # Insert constraints before (check-sat)
        lines = smtlib2_str.split('\n')
        insert_idx = len(lines)
        for i, line in enumerate(lines):
            if line.strip().startswith('(check-sat'):
                insert_idx = i
                break
        
        for constraint in constraints:
            lines.insert(insert_idx, constraint)
            insert_idx += 1
        
        return '\n'.join(lines)


    def run_smt_solver(smtlib2_str: str, solver_name: str = "z3") -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Run an SMT solver on the given SMT-LIB formula.
        Temporarily adds XOR constraints for fused variables to get consistent model values.
        
        Args:
            smtlib2_str: SMT-LIB v2 formula as string
            solver_name: Solver to use ("z3" or "cvc5")
        
        Returns:
            Tuple of (result, model) where:
            - result: "sat", "unsat", or "unknown"
            - model: Dictionary mapping variable names to values (if SAT), None otherwise
        """
        try:
            # Add temporary XOR constraints for fused variables
            smtlib2_str_with_constraints = _add_fused_variable_constraints(smtlib2_str)
            
            parser = SmtLibParser()
            script = parser.get_script(StringIO(smtlib2_str_with_constraints))
            
            assertions = []
            for cmd in script.commands:
                if cmd.name == "assert":
                    assertions.append(cmd.args[0])
            
            if not assertions:
                return "sat", {}
            
            formula = And(assertions) if len(assertions) > 1 else assertions[0]
            
            # Keep solver context open for model extraction
            with Solver(name=solver_name) as s:
                s.add_assertion(formula)
                result = s.solve()
                
                if result:
                    model = s.get_model()
                    model_dict = {}
                    
                    for var_symbol in formula.get_free_variables():
                        var_name = var_symbol.symbol_name()
                        if var_name == "div":  # Skip helpers
                            continue
                        
                        if var_symbol in model:
                            value = model[var_symbol]
                            if value.is_bool_constant():
                                model_dict[var_name] = value.is_true()
                            elif value.is_int_constant():
                                model_dict[var_name] = value.constant_value()
                            else:
                                model_dict[var_name] = str(value)
                    
                    return "sat", model_dict
                else:
                    return "unsat", None
                    
        except SolverReturnedUnknownResultError:
            return "unknown", None
        except Exception as e:
            import traceback
            traceback.print_exc()
            return "unknown", None


    def extract_variables(smtlib2_str: str) -> List[str]:
        """
        Extract all non-fused variable names from SMT-LIB declare-fun commands.
        Fused variables are excluded because they are derived from other variables.
        
        Args:
            smtlib2_str: SMT-LIB v2 formula as string
        
        Returns:
            List of non-fused variable names
        """
        parser = SmtLibParser()
        script = parser.get_script(StringIO(smtlib2_str))
        
        variables = []
        for cmd in script.commands:
            if cmd.name == "declare-fun":
                var_name = str(cmd.args[0])
                # Skip helper functions and fused variables
                if var_name != "div" and not var_name.endswith("_fused"):
                    variables.append(var_name)
        
        return variables


    def select_k_random_variables(all_vars: List[str], k: int, seed: Optional[int] = None) -> Set[str]:
        """
        Randomly select k variables from the list.
        
        Args:
            all_vars: List of all variable names
            k: Number of variables to keep
            seed: Random seed for reproducibility
        
        Returns:
            Set of k variable names to keep
        """
        if k >= len(all_vars):
            return set(all_vars)
        
        if k <= 0:
            return set()
        
        rng = random.Random(seed)
        return set(rng.sample(all_vars, k))


    def generate_random_substitutions(vars_to_replace: List[str], seed: Optional[int] = None) -> Dict[str, bool]:
        """
        Generate random boolean substitutions for UNSAT case.
        
        Args:
            vars_to_replace: List of variable names to replace
            seed: Random seed for reproducibility
        
        Returns:
            Dictionary mapping variable names to random boolean values
        """
        rng = random.Random(seed)
        return {var: rng.choice([True, False]) for var in vars_to_replace}


    def _rename_fused_variables(smtlib2_str: str, substitutions: Dict[str, bool]) -> Tuple[str, Dict[str, bool]]:
        """
        Rename fused variables when their components are being substituted.
        E.g., scr1_x20_scr2_a_fused -> true__scr2_a__orig__scr1_x20_scr2_a_fused if scr1_x20 = true
        
        Args:
            smtlib2_str: SMT-LIB v2 formula as string
            substitutions: Dictionary mapping variable names to boolean values
        
        Returns:
            Tuple of:
            - Modified SMT-LIB string with fused variables renamed
            - Dict of fully unwrapped fused vars to eliminate (mapping to XOR value)
        """
        FUSION_SUFFIX = "_fused"
        
        # Find all fused variable names in the formula
        import re
        fused_pattern = re.compile(r'\b(\w+' + re.escape(FUSION_SUFFIX) + r')\b')
        fused_vars = set(fused_pattern.findall(smtlib2_str))
        
        replacements = {}
        fully_unwrapped_substitutions = {}  # Fused vars to completely eliminate
        
        for fused_var in fused_vars:
            base = fused_var[:-len(FUSION_SUFFIX)]
            
            # Find component variable names
            first = base.find("scr")
            if first == -1:
                continue
            second = base.find("scr", first + 1)
            if second == -1:
                continue
            
            var1 = base[:second]
            if var1.endswith("_"):
                var1 = var1[:-1]
            var2 = base[second:]
            
            # Check if either component is being substituted
            new_var1 = "true" if substitutions.get(var1) is True else ("false" if substitutions.get(var1) is False else var1)
            new_var2 = "true" if substitutions.get(var2) is True else ("false" if substitutions.get(var2) is False else var2)
            
            # If both components are concrete booleans, compute XOR and eliminate the fused variable
            if new_var1 in ("true", "false") and new_var2 in ("true", "false"):
                val1 = (new_var1 == "true")
                val2 = (new_var2 == "true")
                xor_result = val1 != val2  # XOR operation
                fully_unwrapped_substitutions[fused_var] = xor_result
                continue
            
            # If either component changed, create new fused variable name
            # Use special delimiter __ to separate new components from uniqueness suffix
            if new_var1 != var1 or new_var2 != var2:
                original_base = fused_var[:-len(FUSION_SUFFIX)]  # Remove _fused suffix
                new_fused_name = f"{new_var1}__{new_var2}__orig__{original_base}_fused"
                replacements[fused_var] = new_fused_name
        
        # Apply all replacements
        result = smtlib2_str
        for old_name, new_name in replacements.items():
            # Use word boundaries to avoid partial matches
            result = re.sub(r'\b' + re.escape(old_name) + r'\b', new_name, result)
        
        return result, fully_unwrapped_substitutions


    def substitute_variables(smtlib2_str: str, substitutions: Dict[str, Any]) -> str:
        """
        Substitute variables in SMT-LIB formula with concrete values.
        Also renames fused variables when their components are substituted.
        
        Args:
            smtlib2_str: SMT-LIB v2 formula as string
            substitutions: Dictionary mapping variable names to values
        
        Returns:
            Modified SMT-LIB string with substitutions applied
        """
        # First, handle fused variable renaming and get fully unwrapped fused vars to eliminate
        smtlib2_str, fully_unwrapped_fused = _rename_fused_variables(smtlib2_str, substitutions)
        
        # Merge fully unwrapped fused variables into substitutions
        substitutions = {**substitutions, **fully_unwrapped_fused}
        
        parser = SmtLibParser()
        script = parser.get_script(StringIO(smtlib2_str))
        
        symbol_map = {}
        for cmd in script.commands:
            if cmd.name == "assert":
                for var in cmd.args[0].get_free_variables():
                    symbol_map[var.symbol_name()] = var
        
        subs_map = {}
        for var_name, value in substitutions.items():
            if var_name in symbol_map:
                var_symbol = symbol_map[var_name]
                if isinstance(value, bool):
                    subs_map[var_symbol] = TRUE() if value else FALSE()
                elif isinstance(value, int):
                    subs_map[var_symbol] = Int(value)
                else:
                    subs_map[var_symbol] = value
        
        new_commands = []
        
        for cmd in script.commands:
            if cmd.name == "declare-fun":
                var_name = str(cmd.args[0])
                if var_name not in substitutions:  # Skip substituted vars
                    new_commands.append(cmd)
            elif cmd.name == "assert":
                original_formula = cmd.args[0]
                substituted_formula = substitute(original_formula, subs_map)
                new_cmd = SmtLibCommand(name="assert", args=[substituted_formula])
                new_commands.append(new_cmd)
            else:
                new_commands.append(cmd)
        
        script.commands = new_commands
        
        output = StringIO()
        script.serialize(output)
        return output.getvalue()


    # Main logic
    result, model = run_smt_solver(smtlib2_str, solver)
    all_vars = extract_variables(smtlib2_str)
    
    # Verify all variables are Boolean
    parser = SmtLibParser()
    script = parser.get_script(StringIO(smtlib2_str))
    var_types = {}
    for cmd in script.commands:
        if cmd.name == "assert":
            for var in cmd.args[0].get_free_variables():
                var_types[var.symbol_name()] = var.symbol_type()
    
    non_bool_vars = [v for v in all_vars if v in var_types and var_types[v] != BOOL]
    if non_bool_vars:
        raise ValueError(f"Pruning only supports Boolean variables. Found non-Boolean variables: {non_bool_vars}")
    
    if k >= len(all_vars):
        metadata = {
            "pruned": False,
            "reason": f"k ({k}) >= number of variables ({len(all_vars)})",
            "original_vars": len(all_vars),
            "kept_vars": len(all_vars),
            "replaced_vars": 0,
            "original_result": result
        }
        return smtlib2_str, metadata
    
    if k <= 0:
        metadata = {
            "pruned": False,
            "reason": f"k ({k}) <= 0",
            "original_vars": len(all_vars),
            "kept_vars": len(all_vars),
            "replaced_vars": 0,
            "original_result": result
        }
        return smtlib2_str, metadata
    
    if result == "unknown":
        metadata = {
            "pruned": False,
            "reason": "Solver returned unknown",
            "original_vars": len(all_vars),
            "kept_vars": len(all_vars),
            "replaced_vars": 0,
            "original_result": result
        }
        return smtlib2_str, metadata
    
    vars_to_keep = select_k_random_variables(all_vars, k, seed)
    vars_to_replace = [v for v in all_vars if v not in vars_to_keep]
    
    if result == "sat":
        substitutions = {v: model.get(v, False) for v in vars_to_replace}
    else:  # unsat - preserves UNSAT by contradiction
        rng = random.Random(seed)
        substitutions = {v: rng.choice([True, False]) for v in vars_to_replace}
    
    pruned_smtlib = substitute_variables(smtlib2_str, substitutions)
    
    metadata = {
        "pruned": True,
        "original_vars": len(all_vars),
        "kept_vars": k,
        "replaced_vars": len(vars_to_replace),
        "original_result": result,
        "vars_kept": sorted(list(vars_to_keep)),
        "vars_replaced": sorted(vars_to_replace),
        "substitutions": substitutions
    }
    
    return pruned_smtlib, metadata