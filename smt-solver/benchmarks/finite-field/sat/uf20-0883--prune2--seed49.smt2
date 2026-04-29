; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0883--prune2--seed49.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=10 nConstraints=9
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v146 () F)
(declare-fun v262 () F)
(declare-fun v393 () F)
(declare-fun v431 () F)
(declare-fun v703 () F)
(declare-fun v960 () F)
(declare-fun v1268 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v2 v146) (as ff1 F)))
(assert (= (ff.mul v2 v262) (as ff1 F)))
(assert (= (ff.mul v2 v393) (as ff1 F)))
(assert (= (ff.mul v2 v431) (as ff1 F)))
(assert (= (ff.mul v1 v703) (as ff1 F)))
(assert (= (ff.mul v1 v960) (as ff1 F)))
(assert (= (ff.mul v1 v1268) (as ff1 F)))

(check-sat)
