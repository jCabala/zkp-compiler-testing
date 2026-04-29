; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0870--prune3--seed48.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=14 nConstraints=13
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v3 () F)
(declare-fun v319 () F)
(declare-fun v326 () F)
(declare-fun v604 () F)
(declare-fun v612 () F)
(declare-fun v649 () F)
(declare-fun v1066 () F)
(declare-fun v1086 () F)
(declare-fun v1098 () F)
(declare-fun v1175 () F)
(declare-fun v1206 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v3 (ff.add v3 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v3) (as ff0 F)))
(assert (= (ff.mul v2 v3) (ff.add v2 v3 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v319))))
(assert (= (ff.mul v319 v326) (as ff1 F)))
(assert (= (ff.mul v3 v2) (ff.add v2 v3 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v604))))
(assert (= (ff.mul v604 v612) (as ff1 F)))
(assert (= (ff.mul v2 v649) (as ff1 F)))
(assert (= (ff.mul v1 v1066) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v1) (ff.add (as ff1 F) v1 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1086))))
(assert (= (ff.mul v1086 v1098) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v1175) (as ff1 F)))
(assert (= (ff.mul v2 v1206) (as ff1 F)))

(check-sat)
