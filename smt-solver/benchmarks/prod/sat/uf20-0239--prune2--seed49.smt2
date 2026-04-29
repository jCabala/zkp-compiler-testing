; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0239--prune2--seed49.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=13 nConstraints=12
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v208 () F)
(declare-fun v314 () F)
(declare-fun v345 () F)
(declare-fun v410 () F)
(declare-fun v521 () F)
(declare-fun v590 () F)
(declare-fun v679 () F)
(declare-fun v684 () F)
(declare-fun v780 () F)
(declare-fun v1141 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v1 v208) (as ff1 F)))
(assert (= (ff.mul v2 v314) (as ff1 F)))
(assert (= (ff.mul v1 v345) (as ff1 F)))
(assert (= (ff.mul v2 v410) (as ff1 F)))
(assert (= (ff.mul v2 v521) (as ff1 F)))
(assert (= (ff.mul v1 v590) (as ff1 F)))
(assert (= (ff.mul v2 (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1))) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1) v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v679))))
(assert (= (ff.mul v679 v684) (as ff1 F)))
(assert (= (ff.mul v1 v780) (as ff1 F)))
(assert (= (ff.mul v2 v1141) (as ff1 F)))

(check-sat)
