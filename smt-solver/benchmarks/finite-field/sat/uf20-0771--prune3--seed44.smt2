; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0771--prune3--seed44.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=13 nConstraints=12
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v3 () F)
(declare-fun v55 () F)
(declare-fun v116 () F)
(declare-fun v131 () F)
(declare-fun v364 () F)
(declare-fun v532 () F)
(declare-fun v683 () F)
(declare-fun v770 () F)
(declare-fun v1130 () F)
(declare-fun v1198 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v3 (ff.add v3 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v3) (as ff0 F)))
(assert (= (ff.mul v1 v55) (as ff1 F)))
(assert (= (ff.mul v2 v116) (as ff1 F)))
(assert (= (ff.mul v2 v131) (as ff1 F)))
(assert (= (ff.mul v3 v364) (as ff1 F)))
(assert (= (ff.mul v2 v532) (as ff1 F)))
(assert (= (ff.mul v2 v683) (as ff1 F)))
(assert (= (ff.mul v3 v770) (as ff1 F)))
(assert (= (ff.mul v3 v1130) (as ff1 F)))
(assert (= (ff.mul v1 v1198) (as ff1 F)))

(check-sat)
