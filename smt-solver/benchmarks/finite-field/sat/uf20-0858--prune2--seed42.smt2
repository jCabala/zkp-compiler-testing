; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0858--prune2--seed42.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=10 nConstraints=9
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v85 () F)
(declare-fun v280 () F)
(declare-fun v331 () F)
(declare-fun v648 () F)
(declare-fun v833 () F)
(declare-fun v1121 () F)
(declare-fun v1279 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v2 v85) (as ff1 F)))
(assert (= (ff.mul v2 v280) (as ff1 F)))
(assert (= (ff.mul v1 v331) (as ff1 F)))
(assert (= (ff.mul v1 v648) (as ff1 F)))
(assert (= (ff.mul v2 v833) (as ff1 F)))
(assert (= (ff.mul v2 v1121) (as ff1 F)))
(assert (= (ff.mul v2 v1279) (as ff1 F)))

(check-sat)
