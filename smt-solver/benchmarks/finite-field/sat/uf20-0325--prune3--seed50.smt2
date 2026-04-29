; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0325--prune3--seed50.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=15 nConstraints=14
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v3 () F)
(declare-fun v99 () F)
(declare-fun v107 () F)
(declare-fun v112 () F)
(declare-fun v128 () F)
(declare-fun v265 () F)
(declare-fun v270 () F)
(declare-fun v405 () F)
(declare-fun v902 () F)
(declare-fun v1029 () F)
(declare-fun v1130 () F)
(declare-fun v1135 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v3 (ff.add v3 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v3) (as ff0 F)))
(assert (= (ff.mul v3 v99) (as ff1 F)))
(assert (= (ff.mul v2 v3) (ff.add v2 v3 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v107))))
(assert (= (ff.mul v107 v112) (as ff1 F)))
(assert (= (ff.mul v1 v128) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v1) (ff.add (as ff1 F) v1 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v265))))
(assert (= (ff.mul v265 v270) (as ff1 F)))
(assert (= (ff.mul v2 v405) (as ff1 F)))
(assert (= (ff.mul v1 v902) (as ff1 F)))
(assert (= (ff.mul v2 v1029) (as ff1 F)))
(assert (= (ff.mul v2 (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3))) (ff.add (as ff1 F) v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1130))))
(assert (= (ff.mul v1130 v1135) (as ff1 F)))

(check-sat)
