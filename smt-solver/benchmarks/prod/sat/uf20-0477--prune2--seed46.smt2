; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0477--prune2--seed46.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=12 nConstraints=11
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v200 () F)
(declare-fun v245 () F)
(declare-fun v420 () F)
(declare-fun v792 () F)
(declare-fun v811 () F)
(declare-fun v821 () F)
(declare-fun v915 () F)
(declare-fun v1172 () F)
(declare-fun v1201 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v2 v200) (as ff1 F)))
(assert (= (ff.mul v2 v245) (as ff1 F)))
(assert (= (ff.mul v2 v420) (as ff1 F)))
(assert (= (ff.mul v2 v792) (as ff1 F)))
(assert (= (ff.mul v1 v2) (ff.add v1 v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v811))))
(assert (= (ff.mul v811 v821) (as ff1 F)))
(assert (= (ff.mul v2 v915) (as ff1 F)))
(assert (= (ff.mul v1 v1172) (as ff1 F)))
(assert (= (ff.mul v1 v1201) (as ff1 F)))

(check-sat)
