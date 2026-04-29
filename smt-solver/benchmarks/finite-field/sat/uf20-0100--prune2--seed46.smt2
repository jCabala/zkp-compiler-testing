; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0100--prune2--seed46.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=11 nConstraints=10
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v31 () F)
(declare-fun v46 () F)
(declare-fun v243 () F)
(declare-fun v388 () F)
(declare-fun v508 () F)
(declare-fun v590 () F)
(declare-fun v710 () F)
(declare-fun v1269 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v1 v31) (as ff1 F)))
(assert (= (ff.mul v2 v46) (as ff1 F)))
(assert (= (ff.mul v2 v243) (as ff1 F)))
(assert (= (ff.mul v1 v388) (as ff1 F)))
(assert (= (ff.mul v1 v508) (as ff1 F)))
(assert (= (ff.mul v1 v590) (as ff1 F)))
(assert (= (ff.mul v2 v710) (as ff1 F)))
(assert (= (ff.mul v1 v1269) (as ff1 F)))

(check-sat)
