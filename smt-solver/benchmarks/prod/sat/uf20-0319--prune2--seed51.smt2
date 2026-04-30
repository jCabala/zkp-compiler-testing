; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0319--prune2--seed51.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=12 nConstraints=11
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v99 () F)
(declare-fun v130 () F)
(declare-fun v355 () F)
(declare-fun v421 () F)
(declare-fun v707 () F)
(declare-fun v718 () F)
(declare-fun v825 () F)
(declare-fun v935 () F)
(declare-fun v1145 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v1 v99) (as ff1 F)))
(assert (= (ff.mul v2 v130) (as ff1 F)))
(assert (= (ff.mul v2 v355) (as ff1 F)))
(assert (= (ff.mul v2 v421) (as ff1 F)))
(assert (= (ff.mul v1 v707) (as ff1 F)))
(assert (= (ff.mul v1 v718) (as ff1 F)))
(assert (= (ff.mul v1 v825) (as ff1 F)))
(assert (= (ff.mul v2 v935) (as ff1 F)))
(assert (= (ff.mul v2 v1145) (as ff1 F)))

(check-sat)
