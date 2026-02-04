"""
Tests for SMT formula pruning functionality.
"""

import pytest
from src.smt_lib.prune import prune_formula, run_smt_solver


class TestPruningSAT:
    """Test pruning with SAT formulas."""
    
    def test_sat_simple_formula(self):
        """Test pruning a simple SAT Boolean formula."""
        smt = '''(set-logic QF_UF)
        (declare-fun a () Bool)
        (declare-fun b () Bool)
        (declare-fun c () Bool)
        (assert (or a b))
        (assert (=> a c))
        (check-sat)'''
        
        result, metadata = prune_formula(smt, k=2, solver='z3', seed=42)
        
        assert metadata['original_result'] == 'sat'
        assert metadata['pruned'] == True
        assert metadata['kept_vars'] == 2
        assert metadata['replaced_vars'] == 1
        assert len(metadata['vars_kept']) == 2
        
        # Verify SAT preserved
        verify_result, _ = run_smt_solver(result, 'z3')
        assert verify_result == 'sat'
    
    def test_sat_with_xor(self):
        """Test pruning SAT formula with XOR operations."""
        smt = '''(set-logic QF_UF)
        (declare-fun a () Bool)
        (declare-fun b () Bool)
        (declare-fun c () Bool)
        (declare-fun d () Bool)
        (assert (xor a b))
        (assert (or c d))
        (assert (=> a c))
        (check-sat)'''
        
        result, metadata = prune_formula(smt, k=2, solver='z3', seed=42)
        
        assert metadata['original_result'] == 'sat'
        assert metadata['pruned'] == True
        assert metadata['kept_vars'] == 2
        
        # Verify SAT preserved
        verify_result, _ = run_smt_solver(result, 'z3')
        assert verify_result == 'sat'
    
    def test_sat_complex_formula(self):
        """Test pruning complex SAT Boolean formula."""
        smt = '''(set-logic QF_UF)
        (declare-fun a () Bool)
        (declare-fun b () Bool)
        (declare-fun c () Bool)
        (declare-fun d () Bool)
        (declare-fun e () Bool)
        (assert (and (or a b) (or c d)))
        (assert (=> a (not b)))
        (assert (xor d e))
        (check-sat)'''
        
        result, metadata = prune_formula(smt, k=2, solver='z3', seed=123)
        
        assert metadata['original_result'] == 'sat'
        assert metadata['pruned'] == True
        assert metadata['replaced_vars'] == 3
        
        # Verify SAT preserved
        verify_result, _ = run_smt_solver(result, 'z3')
        assert verify_result == 'sat'


class TestPruningUNSAT:
    """Test pruning with UNSAT formulas."""
    
    def test_unsat_simple_formula(self):
        """Test pruning a simple UNSAT Boolean formula."""
        smt = '''(set-logic QF_UF)
        (declare-fun a () Bool)
        (declare-fun b () Bool)
        (declare-fun c () Bool)
        (assert a)
        (assert (not a))
        (assert (or b c))
        (check-sat)'''
        
        result, metadata = prune_formula(smt, k=2, solver='z3', seed=42)
        
        assert metadata['original_result'] == 'unsat'
        assert metadata['pruned'] == True
        assert metadata['kept_vars'] == 2
        
        # Verify UNSAT preserved
        verify_result, _ = run_smt_solver(result, 'z3')
        assert verify_result == 'unsat'
    
    def test_unsat_with_xor(self):
        """Test pruning UNSAT formula with XOR operations."""
        smt = '''(set-logic QF_UF)
        (declare-fun a () Bool)
        (declare-fun b () Bool)
        (declare-fun c () Bool)
        (declare-fun d () Bool)
        (assert (xor a b))
        (assert (not (xor a b)))
        (assert (or c d))
        (check-sat)'''
        
        result, metadata = prune_formula(smt, k=2, solver='z3', seed=123)
        
        assert metadata['original_result'] == 'unsat'
        assert metadata['pruned'] == True
        assert metadata['kept_vars'] == 2
        
        # Verify UNSAT preserved
        verify_result, _ = run_smt_solver(result, 'z3')
        assert verify_result == 'unsat'
    
    def test_unsat_contradiction(self):
        """Test pruning UNSAT formula with direct contradiction."""
        smt = '''(set-logic QF_UF)
        (declare-fun a () Bool)
        (declare-fun b () Bool)
        (declare-fun c () Bool)
        (assert (and a (not a)))
        (assert (xor b c))
        (check-sat)'''
        
        result, metadata = prune_formula(smt, k=1, solver='z3', seed=999)
        
        assert metadata['original_result'] == 'unsat'
        assert metadata['pruned'] == True
        
        # Verify UNSAT preserved
        verify_result, _ = run_smt_solver(result, 'z3')
        assert verify_result == 'unsat'


class TestPruningEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_k_greater_than_n(self):
        """Test when k >= number of variables - should not prune."""
        smt = '''(set-logic QF_UF)
        (declare-fun a () Bool)
        (declare-fun b () Bool)
        (assert (or a b))
        (check-sat)'''
        
        result, metadata = prune_formula(smt, k=5, solver='z3', seed=42)
        
        assert metadata['pruned'] == False
        assert 'k' in metadata['reason']
        assert metadata['original_vars'] == 2
        
        # Verify original satisfiability preserved (no pruning occurred)
        verify_result, _ = run_smt_solver(result, 'z3')
        assert verify_result == metadata['original_result']
    
    def test_k_zero(self):
        """Test when k <= 0 - should not prune."""
        smt = '''(set-logic QF_UF)
        (declare-fun a () Bool)
        (declare-fun b () Bool)
        (assert (or a b))
        (check-sat)'''
        
        result, metadata = prune_formula(smt, k=0, solver='z3', seed=42)
        
        assert metadata['pruned'] == False
        assert 'k' in metadata['reason']
        
        # Verify original satisfiability preserved (no pruning occurred)
        verify_result, _ = run_smt_solver(result, 'z3')
        assert verify_result == metadata['original_result']
        
        # Verify original satisfiability preserved (no pruning occurred)
        verify_result, _ = run_smt_solver(result, 'z3')
        assert verify_result == metadata['original_result']
    
    def test_k_equals_n(self):
        """Test when k equals number of variables - should not prune."""
        smt = '''(set-logic QF_UF)
        (declare-fun a () Bool)
        (declare-fun b () Bool)
        (declare-fun c () Bool)
        (assert (or a b c))
        (check-sat)'''
        
        result, metadata = prune_formula(smt, k=3, solver='z3', seed=42)
        
        assert metadata['pruned'] == False
        assert metadata['original_vars'] == 3
        assert metadata['kept_vars'] == 3
        
        # Verify original satisfiability preserved (no pruning occurred)
        verify_result, _ = run_smt_solver(result, 'z3')
        assert verify_result == metadata['original_result']
        
        # Verify original satisfiability preserved (no pruning occurred)
        verify_result, _ = run_smt_solver(result, 'z3')
        assert verify_result == metadata['original_result']
    
    def test_single_variable_keep_zero(self):
        """Test pruning single variable to zero variables."""
        smt = '''(set-logic QF_UF)
        (declare-fun a () Bool)
        (assert a)
        (check-sat)'''
        
        result, metadata = prune_formula(smt, k=0, solver='z3', seed=42)
        
        assert metadata['pruned'] == False
        
        # Verify original satisfiability preserved (no pruning occurred)
        verify_result, _ = run_smt_solver(result, 'z3')
        assert verify_result == metadata['original_result']
    
    def test_non_boolean_variables_error(self):
        """Test that non-Boolean variables raise an error."""
        smt = '''(set-logic QF_LIA)
        (declare-fun x () Int)
        (declare-fun y () Int)
        (assert (> x 5))
        (assert (< y 10))
        (check-sat)'''
        
        with pytest.raises(ValueError) as exc_info:
            prune_formula(smt, k=1, solver='z3', seed=42)
        
        assert 'Boolean variables' in str(exc_info.value)
        assert 'x' in str(exc_info.value) or 'y' in str(exc_info.value)
    
    def test_mixed_boolean_and_int_error(self):
        """Test that mixed Boolean and Int variables raise an error."""
        smt = '''(set-logic QF_UFLIA)
        (declare-fun a () Bool)
        (declare-fun x () Int)
        (assert a)
        (assert (> x 0))
        (check-sat)'''
        
        with pytest.raises(ValueError) as exc_info:
            prune_formula(smt, k=1, solver='z3', seed=42)
        
        assert 'Boolean variables' in str(exc_info.value)


class TestPruningReproducibility:
    """Test reproducibility with seeds."""
    
    def test_same_seed_same_result(self):
        """Test that same seed produces same pruning."""
        smt = '''(set-logic QF_UF)
        (declare-fun a () Bool)
        (declare-fun b () Bool)
        (declare-fun c () Bool)
        (declare-fun d () Bool)
        (assert (or a b c d))
        (check-sat)'''
        
        result1, metadata1 = prune_formula(smt, k=2, solver='z3', seed=42)
        result2, metadata2 = prune_formula(smt, k=2, solver='z3', seed=42)
        
        assert metadata1['vars_kept'] == metadata2['vars_kept']
        assert metadata1['substitutions'] == metadata2['substitutions']
        
        # Verify both pruned results preserve satisfiability
        verify_result1, _ = run_smt_solver(result1, 'z3')
        verify_result2, _ = run_smt_solver(result2, 'z3')
        assert verify_result1 == metadata1['original_result']
        assert verify_result2 == metadata2['original_result']
    
    def test_different_seed_different_result(self):
        """Test that different seeds produce different pruning."""
        smt = '''(set-logic QF_UF)
        (declare-fun a () Bool)
        (declare-fun b () Bool)
        (declare-fun c () Bool)
        (declare-fun d () Bool)
        (assert (or a b c d))
        (check-sat)'''
        
        result1, metadata1 = prune_formula(smt, k=2, solver='z3', seed=42)
        result2, metadata2 = prune_formula(smt, k=2, solver='z3', seed=999)
        
        # Different seeds should likely (but not guaranteed) produce different results
        # At least verify both are valid
        assert metadata1['pruned'] == True
        assert metadata2['pruned'] == True
        assert len(metadata1['vars_kept']) == 2
        assert len(metadata2['vars_kept']) == 2
        
        # Verify both pruned results preserve satisfiability
        verify_result1, _ = run_smt_solver(result1, 'z3')
        verify_result2, _ = run_smt_solver(result2, 'z3')
        assert verify_result1 == metadata1['original_result']
        assert verify_result2 == metadata2['original_result']


class TestPruningMetadata:
    """Test metadata correctness."""
    
    def test_metadata_structure(self):
        """Test that metadata has all required fields."""
        smt = '''(set-logic QF_UF)
        (declare-fun a () Bool)
        (declare-fun b () Bool)
        (declare-fun c () Bool)
        (assert (or a b c))
        (check-sat)'''
        
        result, metadata = prune_formula(smt, k=2, solver='z3', seed=42)
        
        required_fields = [
            'pruned', 'original_vars', 'kept_vars', 'replaced_vars',
            'original_result', 'vars_kept', 'vars_replaced', 'substitutions'
        ]
        
        for field in required_fields:
            assert field in metadata, f"Missing field: {field}"
        
        # Verify pruned result preserves satisfiability
        verify_result, _ = run_smt_solver(result, 'z3')
        assert verify_result == metadata['original_result']
    
    def test_metadata_counts(self):
        """Test that metadata counts are consistent."""
        smt = '''(set-logic QF_UF)
        (declare-fun a () Bool)
        (declare-fun b () Bool)
        (declare-fun c () Bool)
        (declare-fun d () Bool)
        (declare-fun e () Bool)
        (assert (or a b c d e))
        (check-sat)'''
        
        k = 2
        result, metadata = prune_formula(smt, k=k, solver='z3', seed=42)
        
        assert metadata['original_vars'] == 5
        assert metadata['kept_vars'] == k
        assert metadata['replaced_vars'] == 5 - k
        assert len(metadata['vars_kept']) == k
        assert len(metadata['vars_replaced']) == 5 - k
        assert len(metadata['substitutions']) == 5 - k
        
        # Verify pruned result preserves satisfiability
        verify_result, _ = run_smt_solver(result, 'z3')
        assert verify_result == metadata['original_result']
