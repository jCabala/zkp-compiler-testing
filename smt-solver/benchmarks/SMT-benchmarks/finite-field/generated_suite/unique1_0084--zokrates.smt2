; Auto-generated finite-field SMT-LIB (QF_FF)
; source=smt-solver/benchmarks/SMT-benchmarks/core/unique_sat_1to5vars/unique1_0084.smt2
; backend=zokrates
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=2 nConstraints=2
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)

(assert (= (ff.mul v1 v1) v1))
(assert (= (ff.mul (as ff1 F) (as ff1 F)) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1))))

(check-sat)
