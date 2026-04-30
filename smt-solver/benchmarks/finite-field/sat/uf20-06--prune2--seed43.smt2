; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-06--prune2--seed43.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=11 nConstraints=10
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v51 () F)
(declare-fun v226 () F)
(declare-fun v644 () F)
(declare-fun v907 () F)
(declare-fun v1051 () F)
(declare-fun v1082 () F)
(declare-fun v1256 () F)
(declare-fun v1269 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v2 v51) (as ff1 F)))
(assert (= (ff.mul v1 v226) (as ff1 F)))
(assert (= (ff.mul v1 v644) (as ff1 F)))
(assert (= (ff.mul v2 v907) (as ff1 F)))
(assert (= (ff.mul v2 v1051) (as ff1 F)))
(assert (= (ff.mul v1 v1082) (as ff1 F)))
(assert (= (ff.mul v2 v1256) (as ff1 F)))
(assert (= (ff.mul v1 v1269) (as ff1 F)))

(check-sat)
