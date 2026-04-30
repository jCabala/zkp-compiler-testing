; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0691--prune2--seed51.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=10 nConstraints=9
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v87 () F)
(declare-fun v188 () F)
(declare-fun v277 () F)
(declare-fun v450 () F)
(declare-fun v497 () F)
(declare-fun v615 () F)
(declare-fun v849 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v2 v87) (as ff1 F)))
(assert (= (ff.mul v2 v188) (as ff1 F)))
(assert (= (ff.mul v1 v277) (as ff1 F)))
(assert (= (ff.mul v1 v450) (as ff1 F)))
(assert (= (ff.mul v1 v497) (as ff1 F)))
(assert (= (ff.mul v2 v615) (as ff1 F)))
(assert (= (ff.mul v1 v849) (as ff1 F)))

(check-sat)
