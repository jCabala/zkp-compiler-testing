; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0696--prune2--seed42.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=12 nConstraints=11
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v246 () F)
(declare-fun v251 () F)
(declare-fun v287 () F)
(declare-fun v389 () F)
(declare-fun v415 () F)
(declare-fun v594 () F)
(declare-fun v903 () F)
(declare-fun v1039 () F)
(declare-fun v1196 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v2) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1) v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v246))))
(assert (= (ff.mul v246 v251) (as ff1 F)))
(assert (= (ff.mul v1 v287) (as ff1 F)))
(assert (= (ff.mul v1 v389) (as ff1 F)))
(assert (= (ff.mul v1 v415) (as ff1 F)))
(assert (= (ff.mul v1 v594) (as ff1 F)))
(assert (= (ff.mul v2 v903) (as ff1 F)))
(assert (= (ff.mul v1 v1039) (as ff1 F)))
(assert (= (ff.mul v2 v1196) (as ff1 F)))

(check-sat)
