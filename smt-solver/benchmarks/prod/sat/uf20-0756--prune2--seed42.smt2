; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0756--prune2--seed42.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=12 nConstraints=11
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v93 () F)
(declare-fun v210 () F)
(declare-fun v646 () F)
(declare-fun v686 () F)
(declare-fun v784 () F)
(declare-fun v870 () F)
(declare-fun v1074 () F)
(declare-fun v1178 () F)
(declare-fun v1183 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v1 v93) (as ff1 F)))
(assert (= (ff.mul v1 v210) (as ff1 F)))
(assert (= (ff.mul v1 v646) (as ff1 F)))
(assert (= (ff.mul v1 v686) (as ff1 F)))
(assert (= (ff.mul v2 v784) (as ff1 F)))
(assert (= (ff.mul v2 v870) (as ff1 F)))
(assert (= (ff.mul v1 v1074) (as ff1 F)))
(assert (= (ff.mul v1 v2) (ff.add v1 v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1178))))
(assert (= (ff.mul v1178 v1183) (as ff1 F)))

(check-sat)
