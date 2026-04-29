; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-085--prune2--seed43.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=10 nConstraints=9
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v33 () F)
(declare-fun v125 () F)
(declare-fun v529 () F)
(declare-fun v634 () F)
(declare-fun v1117 () F)
(declare-fun v1140 () F)
(declare-fun v1155 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v2 v33) (as ff1 F)))
(assert (= (ff.mul v1 v125) (as ff1 F)))
(assert (= (ff.mul v1 v529) (as ff1 F)))
(assert (= (ff.mul v1 v634) (as ff1 F)))
(assert (= (ff.mul v1 v1117) (as ff1 F)))
(assert (= (ff.mul v2 v1140) (as ff1 F)))
(assert (= (ff.mul v1 v1155) (as ff1 F)))

(check-sat)
