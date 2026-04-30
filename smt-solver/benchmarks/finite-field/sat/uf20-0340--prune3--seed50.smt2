; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0340--prune3--seed50.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=13 nConstraints=12
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v3 () F)
(declare-fun v70 () F)
(declare-fun v282 () F)
(declare-fun v424 () F)
(declare-fun v521 () F)
(declare-fun v743 () F)
(declare-fun v748 () F)
(declare-fun v1107 () F)
(declare-fun v1181 () F)
(declare-fun v1220 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v3 (ff.add v3 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v3) (as ff0 F)))
(assert (= (ff.mul v1 v70) (as ff1 F)))
(assert (= (ff.mul v3 v1) (ff.add v1 v3 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v282))))
(assert (= (ff.mul v1 v424) (as ff1 F)))
(assert (= (ff.mul v3 v521) (as ff1 F)))
(assert (= (ff.mul v3 v2) (ff.add v2 v3 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v743))))
(assert (= (ff.mul v743 v748) (as ff1 F)))
(assert (= (ff.mul v3 v1107) (as ff1 F)))
(assert (= (ff.mul v3 v1181) (as ff1 F)))
(assert (= (ff.mul v3 v1220) (as ff1 F)))

(check-sat)
