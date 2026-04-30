; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0923--prune2--seed46.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=10 nConstraints=9
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v456 () F)
(declare-fun v501 () F)
(declare-fun v674 () F)
(declare-fun v998 () F)
(declare-fun v1061 () F)
(declare-fun v1229 () F)
(declare-fun v1300 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v2 v456) (as ff1 F)))
(assert (= (ff.mul v1 v501) (as ff1 F)))
(assert (= (ff.mul v1 v674) (as ff1 F)))
(assert (= (ff.mul v1 v998) (as ff1 F)))
(assert (= (ff.mul v2 v1061) (as ff1 F)))
(assert (= (ff.mul v2 v1229) (as ff1 F)))
(assert (= (ff.mul v1 v1300) (as ff1 F)))

(check-sat)
