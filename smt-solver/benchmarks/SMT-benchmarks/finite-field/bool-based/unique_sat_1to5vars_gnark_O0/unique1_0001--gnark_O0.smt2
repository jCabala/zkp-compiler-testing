; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/SMT-benchmarks/core/unique_sat_1to5vars_subset10/unique1_0001.smt2
; backend=gnark
; prime=47
; nVars=4 nConstraints=4
(set-logic QF_FF)

(define-sort F () (_ FiniteField 47))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v3 () F)

(assert (= (ff.mul v1 (ff.add (as ff1 F) (ff.mul (as ff46 F) v1))) (as ff0 F)))
(assert (= (ff.mul (ff.mul (as ff46 F) v1) v3) (ff.add (as ff46 F) v2)))
(assert (= (ff.mul v1 v2) (as ff0 F)))
(assert (= (ff.mul (as ff1 F) v2) (as ff1 F)))

(check-sat)
