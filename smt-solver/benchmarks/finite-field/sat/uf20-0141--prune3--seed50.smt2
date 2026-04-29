; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0141--prune3--seed50.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=15 nConstraints=14
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v3 () F)
(declare-fun v64 () F)
(declare-fun v221 () F)
(declare-fun v284 () F)
(declare-fun v310 () F)
(declare-fun v414 () F)
(declare-fun v642 () F)
(declare-fun v671 () F)
(declare-fun v1156 () F)
(declare-fun v1161 () F)
(declare-fun v1255 () F)
(declare-fun v1286 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v3 (ff.add v3 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v3) (as ff0 F)))
(assert (= (ff.mul v3 (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2))) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2) v3 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v64))))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v221) (as ff1 F)))
(assert (= (ff.mul v1 v284) (as ff1 F)))
(assert (= (ff.mul v3 v2) (ff.add v2 v3 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v310))))
(assert (= (ff.mul v2 v414) (as ff1 F)))
(assert (= (ff.mul v1 v642) (as ff1 F)))
(assert (= (ff.mul v1 v671) (as ff1 F)))
(assert (= (ff.mul v2 (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3))) (ff.add (as ff1 F) v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1156))))
(assert (= (ff.mul v1156 v1161) (as ff1 F)))
(assert (= (ff.mul v1 v1255) (as ff1 F)))
(assert (= (ff.mul v1 v1286) (as ff1 F)))

(check-sat)
