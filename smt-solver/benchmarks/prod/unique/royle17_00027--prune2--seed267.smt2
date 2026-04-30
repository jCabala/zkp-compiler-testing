; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/unique/royle17_00027--prune2--seed267.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=11 nConstraints=10
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v16612 () F)
(declare-fun v25835 () F)
(declare-fun v67322 () F)
(declare-fun v76546 () F)
(declare-fun v77655 () F)
(declare-fun v85960 () F)
(declare-fun v99593 () F)
(declare-fun v104203 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v1 v16612) (as ff1 F)))
(assert (= (ff.mul v2 v25835) (as ff1 F)))
(assert (= (ff.mul v1 v67322) (as ff1 F)))
(assert (= (ff.mul v2 v76546) (as ff1 F)))
(assert (= (ff.mul v1 v77655) (as ff1 F)))
(assert (= (ff.mul v2 v85960) (as ff1 F)))
(assert (= (ff.mul v1 v99593) (as ff1 F)))
(assert (= (ff.mul v2 v104203) (as ff1 F)))

(check-sat)
