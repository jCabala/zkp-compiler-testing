; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0624--prune2--seed42.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=11 nConstraints=10
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v55 () F)
(declare-fun v110 () F)
(declare-fun v141 () F)
(declare-fun v328 () F)
(declare-fun v651 () F)
(declare-fun v744 () F)
(declare-fun v842 () F)
(declare-fun v955 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v2 v55) (as ff1 F)))
(assert (= (ff.mul v1 v110) (as ff1 F)))
(assert (= (ff.mul v1 v141) (as ff1 F)))
(assert (= (ff.mul v2 v328) (as ff1 F)))
(assert (= (ff.mul v2 v651) (as ff1 F)))
(assert (= (ff.mul v1 v744) (as ff1 F)))
(assert (= (ff.mul v1 v842) (as ff1 F)))
(assert (= (ff.mul v2 v955) (as ff1 F)))

(check-sat)
