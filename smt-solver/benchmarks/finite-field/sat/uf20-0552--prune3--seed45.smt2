; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0552--prune3--seed45.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=15 nConstraints=14
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v3 () F)
(declare-fun v220 () F)
(declare-fun v300 () F)
(declare-fun v381 () F)
(declare-fun v386 () F)
(declare-fun v397 () F)
(declare-fun v581 () F)
(declare-fun v782 () F)
(declare-fun v829 () F)
(declare-fun v938 () F)
(declare-fun v1050 () F)
(declare-fun v1090 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v3 (ff.add v3 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v3) (as ff0 F)))
(assert (= (ff.mul v1 v220) (as ff1 F)))
(assert (= (ff.mul v2 v300) (as ff1 F)))
(assert (= (ff.mul v1 v3) (ff.add v1 v3 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v381))))
(assert (= (ff.mul v381 v386) (as ff1 F)))
(assert (= (ff.mul v2 v397) (as ff1 F)))
(assert (= (ff.mul v3 v581) (as ff1 F)))
(assert (= (ff.mul v2 v782) (as ff1 F)))
(assert (= (ff.mul v2 v829) (as ff1 F)))
(assert (= (ff.mul v1 v938) (as ff1 F)))
(assert (= (ff.mul v3 v1050) (as ff1 F)))
(assert (= (ff.mul v2 v1090) (as ff1 F)))

(check-sat)
