; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0783--prune2--seed51.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=11 nConstraints=10
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v239 () F)
(declare-fun v323 () F)
(declare-fun v399 () F)
(declare-fun v599 () F)
(declare-fun v629 () F)
(declare-fun v644 () F)
(declare-fun v923 () F)
(declare-fun v1184 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v1 v239) (as ff1 F)))
(assert (= (ff.mul v2 v323) (as ff1 F)))
(assert (= (ff.mul v2 v399) (as ff1 F)))
(assert (= (ff.mul v1 v599) (as ff1 F)))
(assert (= (ff.mul v1 v629) (as ff1 F)))
(assert (= (ff.mul v2 v644) (as ff1 F)))
(assert (= (ff.mul v2 v923) (as ff1 F)))
(assert (= (ff.mul v1 v1184) (as ff1 F)))

(check-sat)
