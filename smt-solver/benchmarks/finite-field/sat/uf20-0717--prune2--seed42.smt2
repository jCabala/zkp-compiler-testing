; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0717--prune2--seed42.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=14 nConstraints=13
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v165 () F)
(declare-fun v337 () F)
(declare-fun v484 () F)
(declare-fun v534 () F)
(declare-fun v616 () F)
(declare-fun v718 () F)
(declare-fun v726 () F)
(declare-fun v806 () F)
(declare-fun v854 () F)
(declare-fun v1046 () F)
(declare-fun v1053 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v2 v165) (as ff1 F)))
(assert (= (ff.mul v2 v337) (as ff1 F)))
(assert (= (ff.mul v1 v484) (as ff1 F)))
(assert (= (ff.mul v1 v534) (as ff1 F)))
(assert (= (ff.mul v2 v616) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v2) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1) v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v718))))
(assert (= (ff.mul v718 v726) (as ff1 F)))
(assert (= (ff.mul v1 v806) (as ff1 F)))
(assert (= (ff.mul v2 v854) (as ff1 F)))
(assert (= (ff.mul v2 v1) (ff.add v1 v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1046))))
(assert (= (ff.mul v1046 v1053) (as ff1 F)))

(check-sat)
