; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0786--prune2--seed49.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=13 nConstraints=12
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v8 () F)
(declare-fun v9 () F)
(declare-fun v39 () F)
(declare-fun v73 () F)
(declare-fun v397 () F)
(declare-fun v510 () F)
(declare-fun v641 () F)
(declare-fun v765 () F)
(declare-fun v1152 () F)
(declare-fun v1163 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul v8 v9) (as ff1 F)))
(assert (= (ff.mul v2 v39) (as ff1 F)))
(assert (= (ff.mul v2 v73) (as ff1 F)))
(assert (= (ff.mul v2 v397) (as ff1 F)))
(assert (= (ff.mul v1 v510) (as ff1 F)))
(assert (= (ff.mul v1 v641) (as ff1 F)))
(assert (= (ff.mul v2 v765) (as ff1 F)))
(assert (= (ff.mul v2 v1152) (as ff1 F)))
(assert (= (ff.mul v2 v1163) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v2) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1) v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v8))))

(check-sat)
