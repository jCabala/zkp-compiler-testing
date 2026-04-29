; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0702--prune2--seed46.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=13 nConstraints=12
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v221 () F)
(declare-fun v231 () F)
(declare-fun v297 () F)
(declare-fun v369 () F)
(declare-fun v420 () F)
(declare-fun v728 () F)
(declare-fun v884 () F)
(declare-fun v959 () F)
(declare-fun v1046 () F)
(declare-fun v1212 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v2 v1) (ff.add v1 v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v221))))
(assert (= (ff.mul v221 v231) (as ff1 F)))
(assert (= (ff.mul v2 v297) (as ff1 F)))
(assert (= (ff.mul v2 v369) (as ff1 F)))
(assert (= (ff.mul v2 v420) (as ff1 F)))
(assert (= (ff.mul v2 v728) (as ff1 F)))
(assert (= (ff.mul v2 v884) (as ff1 F)))
(assert (= (ff.mul v2 v959) (as ff1 F)))
(assert (= (ff.mul v1 v1046) (as ff1 F)))
(assert (= (ff.mul v2 v1212) (as ff1 F)))

(check-sat)
