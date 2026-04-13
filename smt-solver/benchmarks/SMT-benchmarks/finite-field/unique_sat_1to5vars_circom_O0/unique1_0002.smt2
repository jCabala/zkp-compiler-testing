; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/SMT-benchmarks/core/unique_sat_1to5vars_subset10/unique1_0002.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=9 nConstraints=9
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v3 () F)
(declare-fun v4 () F)
(declare-fun v5 () F)
(declare-fun v6 () F)
(declare-fun v7 () F)
(declare-fun v8 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (as ff0 F) (as ff0 F)) (ff.add v1 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3))))
(assert (= (ff.mul (as ff0 F) (as ff0 F)) (ff.add v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v5))))
(assert (= (ff.mul (as ff0 F) (as ff0 F)) (ff.add v4 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v8))))
(assert (= (ff.mul (as ff0 F) (as ff0 F)) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v7))))
(assert (= (ff.mul (as ff0 F) (as ff0 F)) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3))))
(assert (= (ff.mul v5 v6) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v4))))
(assert (= (ff.mul v5 v4) (as ff0 F)))
(assert (= (ff.mul (as ff0 F) (as ff0 F)) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v7) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v8))))

(check-sat)
