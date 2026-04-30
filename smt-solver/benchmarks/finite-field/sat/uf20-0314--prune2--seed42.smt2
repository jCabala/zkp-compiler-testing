; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0314--prune2--seed42.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=14 nConstraints=13
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v90 () F)
(declare-fun v139 () F)
(declare-fun v213 () F)
(declare-fun v325 () F)
(declare-fun v336 () F)
(declare-fun v354 () F)
(declare-fun v398 () F)
(declare-fun v501 () F)
(declare-fun v863 () F)
(declare-fun v928 () F)
(declare-fun v1126 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v1 v90) (as ff1 F)))
(assert (= (ff.mul v2 v139) (as ff1 F)))
(assert (= (ff.mul v2 v213) (as ff1 F)))
(assert (= (ff.mul v2 v325) (as ff1 F)))
(assert (= (ff.mul v2 v336) (as ff1 F)))
(assert (= (ff.mul v1 v354) (as ff1 F)))
(assert (= (ff.mul v2 v398) (as ff1 F)))
(assert (= (ff.mul v2 v501) (as ff1 F)))
(assert (= (ff.mul v1 v863) (as ff1 F)))
(assert (= (ff.mul v2 v928) (as ff1 F)))
(assert (= (ff.mul v2 v1126) (as ff1 F)))

(check-sat)
