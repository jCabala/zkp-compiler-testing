; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0415--prune2--seed49.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=15 nConstraints=14
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v280 () F)
(declare-fun v510 () F)
(declare-fun v523 () F)
(declare-fun v732 () F)
(declare-fun v897 () F)
(declare-fun v942 () F)
(declare-fun v969 () F)
(declare-fun v999 () F)
(declare-fun v1012 () F)
(declare-fun v1028 () F)
(declare-fun v1089 () F)
(declare-fun v1235 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v1 v280) (as ff1 F)))
(assert (= (ff.mul v2 (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1))) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1) v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v510))))
(assert (= (ff.mul v510 v523) (as ff1 F)))
(assert (= (ff.mul v2 v732) (as ff1 F)))
(assert (= (ff.mul v2 v897) (as ff1 F)))
(assert (= (ff.mul v1 v942) (as ff1 F)))
(assert (= (ff.mul v1 v969) (as ff1 F)))
(assert (= (ff.mul v1 v999) (as ff1 F)))
(assert (= (ff.mul v2 v1012) (as ff1 F)))
(assert (= (ff.mul v1 v1028) (as ff1 F)))
(assert (= (ff.mul v1 v1089) (as ff1 F)))
(assert (= (ff.mul v2 v1235) (as ff1 F)))

(check-sat)
