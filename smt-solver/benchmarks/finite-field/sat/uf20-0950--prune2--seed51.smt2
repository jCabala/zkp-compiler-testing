; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0950--prune2--seed51.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=12 nConstraints=11
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v17 () F)
(declare-fun v117 () F)
(declare-fun v164 () F)
(declare-fun v327 () F)
(declare-fun v491 () F)
(declare-fun v504 () F)
(declare-fun v685 () F)
(declare-fun v745 () F)
(declare-fun v973 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v2 v17) (as ff1 F)))
(assert (= (ff.mul v2 v117) (as ff1 F)))
(assert (= (ff.mul v2 v164) (as ff1 F)))
(assert (= (ff.mul v1 v327) (as ff1 F)))
(assert (= (ff.mul v1 v491) (as ff1 F)))
(assert (= (ff.mul v1 v504) (as ff1 F)))
(assert (= (ff.mul v2 v685) (as ff1 F)))
(assert (= (ff.mul v1 v745) (as ff1 F)))
(assert (= (ff.mul v2 v973) (as ff1 F)))

(check-sat)
