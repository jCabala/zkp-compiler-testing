; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0274--prune2--seed46.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=14 nConstraints=13
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v10 () F)
(declare-fun v34 () F)
(declare-fun v185 () F)
(declare-fun v226 () F)
(declare-fun v589 () F)
(declare-fun v597 () F)
(declare-fun v859 () F)
(declare-fun v874 () F)
(declare-fun v1005 () F)
(declare-fun v1010 () F)
(declare-fun v1162 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v2 v10) (as ff1 F)))
(assert (= (ff.mul v2 v34) (as ff1 F)))
(assert (= (ff.mul v2 v185) (as ff1 F)))
(assert (= (ff.mul v2 v226) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v2) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1) v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v589))))
(assert (= (ff.mul v589 v597) (as ff1 F)))
(assert (= (ff.mul v2 v859) (as ff1 F)))
(assert (= (ff.mul v1 v874) (as ff1 F)))
(assert (= (ff.mul v1 v2) (ff.add v1 v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1005))))
(assert (= (ff.mul v1005 v1010) (as ff1 F)))
(assert (= (ff.mul v2 v1162) (as ff1 F)))

(check-sat)
