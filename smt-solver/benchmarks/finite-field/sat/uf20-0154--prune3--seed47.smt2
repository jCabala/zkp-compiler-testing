; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0154--prune3--seed47.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=13 nConstraints=12
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v3 () F)
(declare-fun v24 () F)
(declare-fun v337 () F)
(declare-fun v430 () F)
(declare-fun v621 () F)
(declare-fun v718 () F)
(declare-fun v960 () F)
(declare-fun v977 () F)
(declare-fun v1005 () F)
(declare-fun v1053 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v3 (ff.add v3 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v3) (as ff0 F)))
(assert (= (ff.mul v1 v24) (as ff1 F)))
(assert (= (ff.mul v3 v337) (as ff1 F)))
(assert (= (ff.mul v2 v430) (as ff1 F)))
(assert (= (ff.mul v2 v621) (as ff1 F)))
(assert (= (ff.mul v3 v718) (as ff1 F)))
(assert (= (ff.mul v3 v960) (as ff1 F)))
(assert (= (ff.mul v1 v977) (as ff1 F)))
(assert (= (ff.mul v1 v1005) (as ff1 F)))
(assert (= (ff.mul v2 v1053) (as ff1 F)))

(check-sat)
