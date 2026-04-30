; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0589--prune2--seed43.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=11 nConstraints=10
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v224 () F)
(declare-fun v229 () F)
(declare-fun v656 () F)
(declare-fun v670 () F)
(declare-fun v685 () F)
(declare-fun v757 () F)
(declare-fun v847 () F)
(declare-fun v881 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v1 v2) (ff.add v1 v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v224))))
(assert (= (ff.mul v224 v229) (as ff1 F)))
(assert (= (ff.mul v1 v656) (as ff1 F)))
(assert (= (ff.mul v2 v670) (as ff1 F)))
(assert (= (ff.mul v2 v685) (as ff1 F)))
(assert (= (ff.mul v2 v757) (as ff1 F)))
(assert (= (ff.mul v1 v847) (as ff1 F)))
(assert (= (ff.mul v1 v881) (as ff1 F)))

(check-sat)
