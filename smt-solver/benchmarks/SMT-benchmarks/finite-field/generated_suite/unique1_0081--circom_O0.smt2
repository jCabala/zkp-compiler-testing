; Auto-generated finite-field SMT-LIB (QF_FF)
; source=smt-solver/benchmarks/SMT-benchmarks/core/unique_sat_1to5vars/unique1_0081.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=7 nConstraints=7
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v3 () F)
(declare-fun v4 () F)
(declare-fun v5 () F)
(declare-fun v6 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (as ff0 F) (as ff0 F)) (ff.add v1 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3))))
(assert (= (ff.mul (as ff0 F) (as ff0 F)) (ff.add v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v6))))
(assert (= (ff.mul (as ff0 F) (as ff0 F)) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v5))))
(assert (= (ff.mul v3 v4) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2))))
(assert (= (ff.mul v3 v2) (as ff0 F)))
(assert (= (ff.mul (as ff0 F) (as ff0 F)) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v5) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v6))))

(check-sat)
