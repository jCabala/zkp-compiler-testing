; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0841--prune2--seed46.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=11 nConstraints=10
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v100 () F)
(declare-fun v131 () F)
(declare-fun v275 () F)
(declare-fun v363 () F)
(declare-fun v405 () F)
(declare-fun v530 () F)
(declare-fun v798 () F)
(declare-fun v1102 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v1 v100) (as ff1 F)))
(assert (= (ff.mul v1 v131) (as ff1 F)))
(assert (= (ff.mul v2 v275) (as ff1 F)))
(assert (= (ff.mul v1 v363) (as ff1 F)))
(assert (= (ff.mul v1 v405) (as ff1 F)))
(assert (= (ff.mul v1 v530) (as ff1 F)))
(assert (= (ff.mul v2 v798) (as ff1 F)))
(assert (= (ff.mul v1 v1102) (as ff1 F)))

(check-sat)
