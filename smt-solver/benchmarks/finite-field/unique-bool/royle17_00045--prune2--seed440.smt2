; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/unique/royle17_00045--prune2--seed440.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=11 nConstraints=10
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v19367 () F)
(declare-fun v19687 () F)
(declare-fun v20709 () F)
(declare-fun v44979 () F)
(declare-fun v57593 () F)
(declare-fun v79618 () F)
(declare-fun v99081 () F)
(declare-fun v102669 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v1 v19367) (as ff1 F)))
(assert (= (ff.mul v2 v19687) (as ff1 F)))
(assert (= (ff.mul v1 v20709) (as ff1 F)))
(assert (= (ff.mul v2 v44979) (as ff1 F)))
(assert (= (ff.mul v1 v57593) (as ff1 F)))
(assert (= (ff.mul v2 v79618) (as ff1 F)))
(assert (= (ff.mul v1 v99081) (as ff1 F)))
(assert (= (ff.mul v2 v102669) (as ff1 F)))

(check-sat)
