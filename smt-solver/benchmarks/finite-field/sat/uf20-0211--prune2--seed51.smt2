; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0211--prune2--seed51.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=13 nConstraints=12
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v46 () F)
(declare-fun v222 () F)
(declare-fun v358 () F)
(declare-fun v439 () F)
(declare-fun v454 () F)
(declare-fun v647 () F)
(declare-fun v652 () F)
(declare-fun v663 () F)
(declare-fun v835 () F)
(declare-fun v1114 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v1 v46) (as ff1 F)))
(assert (= (ff.mul v2 v222) (as ff1 F)))
(assert (= (ff.mul v2 v358) (as ff1 F)))
(assert (= (ff.mul v1 v439) (as ff1 F)))
(assert (= (ff.mul v2 v454) (as ff1 F)))
(assert (= (ff.mul v2 (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1))) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1) v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v647))))
(assert (= (ff.mul v647 v652) (as ff1 F)))
(assert (= (ff.mul v2 v663) (as ff1 F)))
(assert (= (ff.mul v1 v835) (as ff1 F)))
(assert (= (ff.mul v2 v1114) (as ff1 F)))

(check-sat)
