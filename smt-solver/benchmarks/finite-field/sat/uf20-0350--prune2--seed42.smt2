; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0350--prune2--seed42.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=11 nConstraints=10
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v62 () F)
(declare-fun v92 () F)
(declare-fun v125 () F)
(declare-fun v367 () F)
(declare-fun v424 () F)
(declare-fun v611 () F)
(declare-fun v998 () F)
(declare-fun v1071 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v1 v2) (ff.add v1 v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v62))))
(assert (= (ff.mul v62 v92) (as ff1 F)))
(assert (= (ff.mul v2 v125) (as ff1 F)))
(assert (= (ff.mul v2 v367) (as ff1 F)))
(assert (= (ff.mul v1 v424) (as ff1 F)))
(assert (= (ff.mul v1 v611) (as ff1 F)))
(assert (= (ff.mul v2 v998) (as ff1 F)))
(assert (= (ff.mul v1 v1071) (as ff1 F)))

(check-sat)
