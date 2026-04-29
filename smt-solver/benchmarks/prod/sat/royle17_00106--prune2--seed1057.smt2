; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/unique/royle17_00106--prune2--seed1057.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=12 nConstraints=11
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v4834 () F)
(declare-fun v5345 () F)
(declare-fun v46324 () F)
(declare-fun v49396 () F)
(declare-fun v58616 () F)
(declare-fun v97034 () F)
(declare-fun v127768 () F)
(declare-fun v138527 () F)
(declare-fun v139084 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v1 v4834) (as ff1 F)))
(assert (= (ff.mul v2 v5345) (as ff1 F)))
(assert (= (ff.mul v1 v46324) (as ff1 F)))
(assert (= (ff.mul v2 v49396) (as ff1 F)))
(assert (= (ff.mul v2 v58616) (as ff1 F)))
(assert (= (ff.mul v1 v97034) (as ff1 F)))
(assert (= (ff.mul v2 v127768) (as ff1 F)))
(assert (= (ff.mul v1 v138527) (as ff1 F)))
(assert (= (ff.mul v2 v139084) (as ff1 F)))

(check-sat)
