; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0667--prune2--seed51.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=12 nConstraints=11
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v216 () F)
(declare-fun v221 () F)
(declare-fun v486 () F)
(declare-fun v598 () F)
(declare-fun v763 () F)
(declare-fun v1060 () F)
(declare-fun v1065 () F)
(declare-fun v1201 () F)
(declare-fun v1253 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v1 v2) (ff.add v1 v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v216))))
(assert (= (ff.mul v216 v221) (as ff1 F)))
(assert (= (ff.mul v2 v486) (as ff1 F)))
(assert (= (ff.mul v2 v598) (as ff1 F)))
(assert (= (ff.mul v1 v763) (as ff1 F)))
(assert (= (ff.mul v1 v2) (ff.add v1 v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1060))))
(assert (= (ff.mul v1060 v1065) (as ff1 F)))
(assert (= (ff.mul v1 v1201) (as ff1 F)))
(assert (= (ff.mul v2 v1253) (as ff1 F)))

(check-sat)
