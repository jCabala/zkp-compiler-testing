; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/unique/royle17_00140--prune2--seed1396.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=12 nConstraints=11
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v1760 () F)
(declare-fun v14246 () F)
(declare-fun v15588 () F)
(declare-fun v42738 () F)
(declare-fun v65789 () F)
(declare-fun v93961 () F)
(declare-fun v107788 () F)
(declare-fun v125713 () F)
(declare-fun v139018 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v2 v1760) (as ff1 F)))
(assert (= (ff.mul v1 v14246) (as ff1 F)))
(assert (= (ff.mul v1 v15588) (as ff1 F)))
(assert (= (ff.mul v2 v42738) (as ff1 F)))
(assert (= (ff.mul v2 v65789) (as ff1 F)))
(assert (= (ff.mul v1 v93961) (as ff1 F)))
(assert (= (ff.mul v1 v107788) (as ff1 F)))
(assert (= (ff.mul v2 v125713) (as ff1 F)))
(assert (= (ff.mul v1 v139018) (as ff1 F)))

(check-sat)
