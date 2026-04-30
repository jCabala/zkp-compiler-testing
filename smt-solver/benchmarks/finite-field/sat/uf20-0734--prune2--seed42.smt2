; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0734--prune2--seed42.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=15 nConstraints=14
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v121 () F)
(declare-fun v301 () F)
(declare-fun v306 () F)
(declare-fun v628 () F)
(declare-fun v747 () F)
(declare-fun v866 () F)
(declare-fun v897 () F)
(declare-fun v941 () F)
(declare-fun v1039 () F)
(declare-fun v1079 () F)
(declare-fun v1094 () F)
(declare-fun v1105 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v1 v121) (as ff1 F)))
(assert (= (ff.mul v2 (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1))) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1) v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v301))))
(assert (= (ff.mul v301 v306) (as ff1 F)))
(assert (= (ff.mul v1 v628) (as ff1 F)))
(assert (= (ff.mul v2 v747) (as ff1 F)))
(assert (= (ff.mul v1 v866) (as ff1 F)))
(assert (= (ff.mul v2 v897) (as ff1 F)))
(assert (= (ff.mul v2 v941) (as ff1 F)))
(assert (= (ff.mul v2 v1039) (as ff1 F)))
(assert (= (ff.mul v1 v1079) (as ff1 F)))
(assert (= (ff.mul v1 v1094) (as ff1 F)))
(assert (= (ff.mul v1 v1105) (as ff1 F)))

(check-sat)
