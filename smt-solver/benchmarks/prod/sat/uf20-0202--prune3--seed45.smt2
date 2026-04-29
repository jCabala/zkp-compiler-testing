; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0202--prune3--seed45.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=14 nConstraints=13
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v3 () F)
(declare-fun v573 () F)
(declare-fun v615 () F)
(declare-fun v623 () F)
(declare-fun v822 () F)
(declare-fun v827 () F)
(declare-fun v855 () F)
(declare-fun v873 () F)
(declare-fun v1066 () F)
(declare-fun v1184 () F)
(declare-fun v1189 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v3 (ff.add v3 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v3) (as ff0 F)))
(assert (= (ff.mul v1 v573) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v1) (ff.add (as ff1 F) v1 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v615))))
(assert (= (ff.mul v615 v623) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2))) (ff.add (as ff2 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v822))))
(assert (= (ff.mul v822 v827) (as ff1 F)))
(assert (= (ff.mul v2 v855) (as ff1 F)))
(assert (= (ff.mul v1 v873) (as ff1 F)))
(assert (= (ff.mul v1 v1066) (as ff1 F)))
(assert (= (ff.mul v2 v3) (ff.add v2 v3 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1184))))
(assert (= (ff.mul v1184 v1189) (as ff1 F)))

(check-sat)
