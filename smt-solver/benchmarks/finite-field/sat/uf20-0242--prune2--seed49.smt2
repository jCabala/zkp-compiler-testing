; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0242--prune2--seed49.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=11 nConstraints=10
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v46 () F)
(declare-fun v103 () F)
(declare-fun v516 () F)
(declare-fun v730 () F)
(declare-fun v757 () F)
(declare-fun v812 () F)
(declare-fun v922 () F)
(declare-fun v1228 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v2 v46) (as ff1 F)))
(assert (= (ff.mul v2 v103) (as ff1 F)))
(assert (= (ff.mul v1 v516) (as ff1 F)))
(assert (= (ff.mul v2 v730) (as ff1 F)))
(assert (= (ff.mul v1 v757) (as ff1 F)))
(assert (= (ff.mul v1 v812) (as ff1 F)))
(assert (= (ff.mul v2 v922) (as ff1 F)))
(assert (= (ff.mul v2 v1228) (as ff1 F)))

(check-sat)
