; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0236--prune3--seed47.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=15 nConstraints=14
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v3 () F)
(declare-fun v103 () F)
(declare-fun v138 () F)
(declare-fun v247 () F)
(declare-fun v422 () F)
(declare-fun v484 () F)
(declare-fun v695 () F)
(declare-fun v746 () F)
(declare-fun v804 () F)
(declare-fun v853 () F)
(declare-fun v870 () F)
(declare-fun v1206 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v3 (ff.add v3 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v3) (as ff0 F)))
(assert (= (ff.mul v1 v103) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v3) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1) v3 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v138))))
(assert (= (ff.mul v3 v247) (as ff1 F)))
(assert (= (ff.mul v1 v422) (as ff1 F)))
(assert (= (ff.mul v1 v484) (as ff1 F)))
(assert (= (ff.mul v1 v695) (as ff1 F)))
(assert (= (ff.mul v2 v746) (as ff1 F)))
(assert (= (ff.mul v3 v804) (as ff1 F)))
(assert (= (ff.mul v2 v853) (as ff1 F)))
(assert (= (ff.mul v3 v870) (as ff1 F)))
(assert (= (ff.mul v3 v1206) (as ff1 F)))

(check-sat)
