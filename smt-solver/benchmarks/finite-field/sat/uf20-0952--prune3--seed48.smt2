; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0952--prune3--seed48.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=15 nConstraints=14
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v3 () F)
(declare-fun v82 () F)
(declare-fun v87 () F)
(declare-fun v136 () F)
(declare-fun v168 () F)
(declare-fun v201 () F)
(declare-fun v209 () F)
(declare-fun v214 () F)
(declare-fun v579 () F)
(declare-fun v610 () F)
(declare-fun v621 () F)
(declare-fun v1014 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v3 (ff.add v3 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v3) (as ff0 F)))
(assert (= (ff.mul v3 v1) (ff.add v1 v3 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v82))))
(assert (= (ff.mul v82 v87) (as ff1 F)))
(assert (= (ff.mul v3 v136) (as ff1 F)))
(assert (= (ff.mul v1 v168) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v1) (ff.add (as ff1 F) v1 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v201))))
(assert (= (ff.mul v201 (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3))) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3) v201 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v209))))
(assert (= (ff.mul v209 v214) (as ff1 F)))
(assert (= (ff.mul v2 v579) (as ff1 F)))
(assert (= (ff.mul v2 v610) (as ff1 F)))
(assert (= (ff.mul v3 v621) (as ff1 F)))
(assert (= (ff.mul v1 v1014) (as ff1 F)))

(check-sat)
