; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0539--prune2--seed46.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=10 nConstraints=9
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v291 () F)
(declare-fun v313 () F)
(declare-fun v424 () F)
(declare-fun v438 () F)
(declare-fun v853 () F)
(declare-fun v1134 () F)
(declare-fun v1198 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v2 v291) (as ff1 F)))
(assert (= (ff.mul v1 v313) (as ff1 F)))
(assert (= (ff.mul v2 v424) (as ff1 F)))
(assert (= (ff.mul v2 v438) (as ff1 F)))
(assert (= (ff.mul v1 v853) (as ff1 F)))
(assert (= (ff.mul v1 v1134) (as ff1 F)))
(assert (= (ff.mul v2 v1198) (as ff1 F)))

(check-sat)
