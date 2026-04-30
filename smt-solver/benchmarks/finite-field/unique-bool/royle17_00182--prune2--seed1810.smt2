; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/unique/royle17_00182--prune2--seed1810.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=12 nConstraints=11
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v14052 () F)
(declare-fun v14246 () F)
(declare-fun v18147 () F)
(declare-fun v51957 () F)
(declare-fun v93448 () F)
(declare-fun v96522 () F)
(declare-fun v110350 () F)
(declare-fun v134942 () F)
(declare-fun v139018 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v2 v14052) (as ff1 F)))
(assert (= (ff.mul v1 v14246) (as ff1 F)))
(assert (= (ff.mul v1 v18147) (as ff1 F)))
(assert (= (ff.mul v2 v51957) (as ff1 F)))
(assert (= (ff.mul v2 v93448) (as ff1 F)))
(assert (= (ff.mul v1 v96522) (as ff1 F)))
(assert (= (ff.mul v1 v110350) (as ff1 F)))
(assert (= (ff.mul v2 v134942) (as ff1 F)))
(assert (= (ff.mul v1 v139018) (as ff1 F)))

(check-sat)
