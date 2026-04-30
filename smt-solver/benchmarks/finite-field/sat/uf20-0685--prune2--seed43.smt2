; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0685--prune2--seed43.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=16 nConstraints=15
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v152 () F)
(declare-fun v291 () F)
(declare-fun v398 () F)
(declare-fun v403 () F)
(declare-fun v498 () F)
(declare-fun v643 () F)
(declare-fun v656 () F)
(declare-fun v809 () F)
(declare-fun v849 () F)
(declare-fun v882 () F)
(declare-fun v1188 () F)
(declare-fun v1201 () F)
(declare-fun v1244 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v1) (ff.add (as ff1 F) v1 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v152))))
(assert (= (ff.mul v1 v291) (as ff1 F)))
(assert (= (ff.mul v2 (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1))) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1) v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v398))))
(assert (= (ff.mul v398 v403) (as ff1 F)))
(assert (= (ff.mul v2 v498) (as ff1 F)))
(assert (= (ff.mul v1 v643) (as ff1 F)))
(assert (= (ff.mul v2 v656) (as ff1 F)))
(assert (= (ff.mul v1 v809) (as ff1 F)))
(assert (= (ff.mul v2 v849) (as ff1 F)))
(assert (= (ff.mul v2 v882) (as ff1 F)))
(assert (= (ff.mul v2 v1188) (as ff1 F)))
(assert (= (ff.mul v2 v1201) (as ff1 F)))
(assert (= (ff.mul v2 v1244) (as ff1 F)))

(check-sat)
