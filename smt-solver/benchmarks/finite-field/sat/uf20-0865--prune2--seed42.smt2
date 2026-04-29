; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0865--prune2--seed42.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=12 nConstraints=11
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v122 () F)
(declare-fun v336 () F)
(declare-fun v494 () F)
(declare-fun v550 () F)
(declare-fun v555 () F)
(declare-fun v566 () F)
(declare-fun v672 () F)
(declare-fun v1203 () F)
(declare-fun v1216 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v1 v122) (as ff1 F)))
(assert (= (ff.mul v1 v336) (as ff1 F)))
(assert (= (ff.mul v2 v494) (as ff1 F)))
(assert (= (ff.mul v1 (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2))) (ff.add (as ff1 F) v1 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v550))))
(assert (= (ff.mul v550 v555) (as ff1 F)))
(assert (= (ff.mul v1 v566) (as ff1 F)))
(assert (= (ff.mul v1 v672) (as ff1 F)))
(assert (= (ff.mul v2 v1203) (as ff1 F)))
(assert (= (ff.mul v2 v1216) (as ff1 F)))

(check-sat)
