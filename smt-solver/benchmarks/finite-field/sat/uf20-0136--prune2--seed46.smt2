; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0136--prune2--seed46.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=10 nConstraints=9
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v321 () F)
(declare-fun v480 () F)
(declare-fun v841 () F)
(declare-fun v846 () F)
(declare-fun v969 () F)
(declare-fun v1027 () F)
(declare-fun v1182 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v1 v321) (as ff1 F)))
(assert (= (ff.mul v2 v480) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v1) (ff.add (as ff1 F) v1 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v841))))
(assert (= (ff.mul v841 v846) (as ff1 F)))
(assert (= (ff.mul v2 v969) (as ff1 F)))
(assert (= (ff.mul v2 v1027) (as ff1 F)))
(assert (= (ff.mul v2 v1182) (as ff1 F)))

(check-sat)
