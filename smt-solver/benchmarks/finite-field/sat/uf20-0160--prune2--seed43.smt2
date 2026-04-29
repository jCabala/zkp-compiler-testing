; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0160--prune2--seed43.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=9 nConstraints=8
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v10 () F)
(declare-fun v333 () F)
(declare-fun v341 () F)
(declare-fun v572 () F)
(declare-fun v770 () F)
(declare-fun v1177 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v10) (as ff1 F)))
(assert (= (ff.mul v2 v1) (ff.add v1 v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v333))))
(assert (= (ff.mul v333 v341) (as ff1 F)))
(assert (= (ff.mul v1 v572) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v770) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v1177) (as ff1 F)))

(check-sat)
