; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0920--prune3--seed44.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=15 nConstraints=14
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v3 () F)
(declare-fun v210 () F)
(declare-fun v307 () F)
(declare-fun v606 () F)
(declare-fun v635 () F)
(declare-fun v663 () F)
(declare-fun v696 () F)
(declare-fun v699 () F)
(declare-fun v762 () F)
(declare-fun v937 () F)
(declare-fun v945 () F)
(declare-fun v1248 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v3 (ff.add v3 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v3) (as ff0 F)))
(assert (= (ff.mul v3 v210) (as ff1 F)))
(assert (= (ff.mul v3 v307) (as ff1 F)))
(assert (= (ff.mul v2 v606) (as ff1 F)))
(assert (= (ff.mul v3 v635) (as ff1 F)))
(assert (= (ff.mul v3 v663) (as ff1 F)))
(assert (= (ff.mul v3 v696) (as ff1 F)))
(assert (= (ff.mul v1 v699) (as ff1 F)))
(assert (= (ff.mul v1 v762) (as ff1 F)))
(assert (= (ff.mul v2 (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3))) (ff.add (as ff1 F) v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v937))))
(assert (= (ff.mul v937 v945) (as ff1 F)))
(assert (= (ff.mul v3 v1248) (as ff1 F)))

(check-sat)
