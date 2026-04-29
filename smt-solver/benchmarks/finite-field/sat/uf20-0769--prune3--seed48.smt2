; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0769--prune3--seed48.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=14 nConstraints=13
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v3 () F)
(declare-fun v373 () F)
(declare-fun v529 () F)
(declare-fun v534 () F)
(declare-fun v551 () F)
(declare-fun v669 () F)
(declare-fun v710 () F)
(declare-fun v723 () F)
(declare-fun v1003 () F)
(declare-fun v1035 () F)
(declare-fun v1244 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v3 (ff.add v3 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v3) (as ff0 F)))
(assert (= (ff.mul v1 v373) (as ff1 F)))
(assert (= (ff.mul v1 v2) (ff.add v1 v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v529))))
(assert (= (ff.mul v529 v534) (as ff1 F)))
(assert (= (ff.mul v1 v551) (as ff1 F)))
(assert (= (ff.mul v2 v669) (as ff1 F)))
(assert (= (ff.mul v2 v710) (as ff1 F)))
(assert (= (ff.mul v1 v723) (as ff1 F)))
(assert (= (ff.mul v2 v1003) (as ff1 F)))
(assert (= (ff.mul v2 v1035) (as ff1 F)))
(assert (= (ff.mul v1 v1244) (as ff1 F)))

(check-sat)
