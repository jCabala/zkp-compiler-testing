; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0785--prune3--seed47.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=13 nConstraints=12
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v3 () F)
(declare-fun v36 () F)
(declare-fun v227 () F)
(declare-fun v284 () F)
(declare-fun v491 () F)
(declare-fun v584 () F)
(declare-fun v819 () F)
(declare-fun v830 () F)
(declare-fun v1185 () F)
(declare-fun v1190 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v3 (ff.add v3 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v3) (as ff0 F)))
(assert (= (ff.mul v2 v36) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v227) (as ff1 F)))
(assert (= (ff.mul v1 v284) (as ff1 F)))
(assert (= (ff.mul v1 v491) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v584) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3))) (ff.add (as ff2 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v819))))
(assert (= (ff.mul v819 v830) (as ff1 F)))
(assert (= (ff.mul v1 v3) (ff.add v1 v3 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1185))))
(assert (= (ff.mul v1185 v1190) (as ff1 F)))

(check-sat)
