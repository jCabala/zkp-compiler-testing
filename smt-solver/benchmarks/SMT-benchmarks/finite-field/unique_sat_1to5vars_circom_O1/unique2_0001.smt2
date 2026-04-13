; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/SMT-benchmarks/core/unique_sat_1to5vars_subset10/unique2_0001.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=9 nConstraints=10
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v3 () F)
(declare-fun v5 () F)
(declare-fun v7 () F)
(declare-fun v10 () F)
(declare-fun v12 () F)
(declare-fun v14 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v3 v7) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v5))))
(assert (= (ff.mul v3 v5) (as ff0 F)))
(assert (= (ff.mul v10 v14) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v12))))
(assert (= (ff.mul v10 v12) (as ff0 F)))
(assert (= (ff.mul (as ff0 F) (as ff0 F)) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3))))
(assert (= (ff.mul (as ff0 F) (as ff0 F)) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v5)))
(assert (= (ff.mul (as ff0 F) (as ff0 F)) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v10))))
(assert (= (ff.mul (as ff0 F) (as ff0 F)) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v12)))

(check-sat)
