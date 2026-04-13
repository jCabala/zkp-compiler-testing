; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/SMT-benchmarks/core/unique_sat_1to5vars_subset10/unique4_0001.smt2
; backend=gnark
; prime=47
; nVars=13 nConstraints=16
(set-logic QF_FF)

(define-sort F () (_ FiniteField 47))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v3 () F)
(declare-fun v4 () F)
(declare-fun v5 () F)
(declare-fun v6 () F)
(declare-fun v7 () F)
(declare-fun v8 () F)
(declare-fun v9 () F)
(declare-fun v10 () F)
(declare-fun v11 () F)
(declare-fun v12 () F)

(assert (= (ff.mul v1 (ff.add (as ff1 F) (ff.mul (as ff46 F) v1))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add (as ff1 F) (ff.mul (as ff46 F) v2))) (as ff0 F)))
(assert (= (ff.mul v3 (ff.add (as ff1 F) (ff.mul (as ff46 F) v3))) (as ff0 F)))
(assert (= (ff.mul v4 (ff.add (as ff1 F) (ff.mul (as ff46 F) v4))) (as ff0 F)))
(assert (= (ff.mul (ff.mul (as ff46 F) v3) v6) (ff.add (as ff46 F) v5)))
(assert (= (ff.mul v3 v5) (as ff0 F)))
(assert (= (ff.mul (as ff1 F) v5) (as ff1 F)))
(assert (= (ff.mul (as ff1 F) v1) (as ff1 F)))
(assert (= (ff.mul (ff.mul (as ff46 F) v1) v8) (ff.add (as ff46 F) v7)))
(assert (= (ff.mul v1 v7) (as ff0 F)))
(assert (= (ff.mul v7 v3) (ff.add (ff.mul (as ff46 F) v9) v7 v3)))
(assert (= (ff.mul (ff.mul (as ff46 F) v4) v11) (ff.add (as ff46 F) v10)))
(assert (= (ff.mul v4 v10) (as ff0 F)))
(assert (= (ff.mul v9 v10) (ff.add (ff.mul (as ff46 F) v12) v9 v10)))
(assert (= (ff.mul (as ff1 F) v12) (as ff1 F)))
(assert (= (ff.mul (as ff1 F) v2) (as ff1 F)))

(check-sat)
