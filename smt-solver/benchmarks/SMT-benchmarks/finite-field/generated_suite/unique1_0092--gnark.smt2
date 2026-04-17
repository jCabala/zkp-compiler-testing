; Auto-generated finite-field SMT-LIB (QF_FF)
; source=smt-solver/benchmarks/SMT-benchmarks/core/unique_sat_1to5vars/unique1_0092.smt2
; backend=gnark
; prime=47
; nVars=2 nConstraints=2
(set-logic QF_FF)

(define-sort F () (_ FiniteField 47))

(declare-fun v1 () F)

(assert (= (ff.mul v1 (ff.add (as ff1 F) (ff.mul (as ff46 F) v1))) (as ff0 F)))
(assert (= (ff.mul (as ff1 F) v1) (as ff1 F)))

(check-sat)
