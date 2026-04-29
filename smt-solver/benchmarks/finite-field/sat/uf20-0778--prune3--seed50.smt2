; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0778--prune3--seed50.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=12 nConstraints=11
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v3 () F)
(declare-fun v301 () F)
(declare-fun v429 () F)
(declare-fun v647 () F)
(declare-fun v954 () F)
(declare-fun v1028 () F)
(declare-fun v1033 () F)
(declare-fun v1096 () F)
(declare-fun v1214 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v3 (ff.add v3 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v3) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v301) (as ff1 F)))
(assert (= (ff.mul v3 v429) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v647) (as ff1 F)))
(assert (= (ff.mul v3 v954) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2))) (ff.add (as ff2 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1028))))
(assert (= (ff.mul v1028 v1033) (as ff1 F)))
(assert (= (ff.mul v1 v1096) (as ff1 F)))
(assert (= (ff.mul v3 v1214) (as ff1 F)))

(check-sat)
