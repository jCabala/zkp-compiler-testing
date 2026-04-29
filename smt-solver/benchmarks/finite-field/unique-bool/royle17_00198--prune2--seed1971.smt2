; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/unique/royle17_00198--prune2--seed1971.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=12 nConstraints=11
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v14246 () F)
(declare-fun v14566 () F)
(declare-fun v25835 () F)
(declare-fun v76546 () F)
(declare-fun v85960 () F)
(declare-fun v92937 () F)
(declare-fun v104203 () F)
(declare-fun v106765 () F)
(declare-fun v139018 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v1 v14246) (as ff1 F)))
(assert (= (ff.mul v1 v14566) (as ff1 F)))
(assert (= (ff.mul v2 v25835) (as ff1 F)))
(assert (= (ff.mul v2 v76546) (as ff1 F)))
(assert (= (ff.mul v2 v85960) (as ff1 F)))
(assert (= (ff.mul v1 v92937) (as ff1 F)))
(assert (= (ff.mul v2 v104203) (as ff1 F)))
(assert (= (ff.mul v1 v106765) (as ff1 F)))
(assert (= (ff.mul v1 v139018) (as ff1 F)))

(check-sat)
