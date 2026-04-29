; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0549--prune2--seed51.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=14 nConstraints=13
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v210 () F)
(declare-fun v218 () F)
(declare-fun v231 () F)
(declare-fun v299 () F)
(declare-fun v306 () F)
(declare-fun v445 () F)
(declare-fun v581 () F)
(declare-fun v851 () F)
(declare-fun v887 () F)
(declare-fun v1008 () F)
(declare-fun v1026 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v2 v1) (ff.add v1 v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v210))))
(assert (= (ff.mul v210 v218) (as ff1 F)))
(assert (= (ff.mul v1 v231) (as ff1 F)))
(assert (= (ff.mul v2 v299) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2))) (ff.add (as ff2 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v306))))
(assert (= (ff.mul v2 v445) (as ff1 F)))
(assert (= (ff.mul v2 v581) (as ff1 F)))
(assert (= (ff.mul v2 v851) (as ff1 F)))
(assert (= (ff.mul v1 v887) (as ff1 F)))
(assert (= (ff.mul v2 v1008) (as ff1 F)))
(assert (= (ff.mul v2 v1026) (as ff1 F)))

(check-sat)
