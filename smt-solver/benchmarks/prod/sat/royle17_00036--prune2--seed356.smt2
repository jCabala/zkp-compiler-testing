; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/unique/royle17_00036--prune2--seed356.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=11 nConstraints=10
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v10468 () F)
(declare-fun v17636 () F)
(declare-fun v55545 () F)
(declare-fun v64762 () F)
(declare-fun v77570 () F)
(declare-fun v105228 () F)
(declare-fun v129304 () F)
(declare-fun v143203 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v2 v10468) (as ff1 F)))
(assert (= (ff.mul v1 v17636) (as ff1 F)))
(assert (= (ff.mul v2 v55545) (as ff1 F)))
(assert (= (ff.mul v2 v64762) (as ff1 F)))
(assert (= (ff.mul v1 v77570) (as ff1 F)))
(assert (= (ff.mul v1 v105228) (as ff1 F)))
(assert (= (ff.mul v2 v129304) (as ff1 F)))
(assert (= (ff.mul v1 v143203) (as ff1 F)))

(check-sat)
