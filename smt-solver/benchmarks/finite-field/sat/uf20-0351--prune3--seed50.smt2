; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0351--prune3--seed50.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=14 nConstraints=13
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v3 () F)
(declare-fun v121 () F)
(declare-fun v338 () F)
(declare-fun v343 () F)
(declare-fun v420 () F)
(declare-fun v512 () F)
(declare-fun v725 () F)
(declare-fun v767 () F)
(declare-fun v942 () F)
(declare-fun v1024 () F)
(declare-fun v1110 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v3 (ff.add v3 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v3) (as ff0 F)))
(assert (= (ff.mul v3 v121) (as ff1 F)))
(assert (= (ff.mul v2 v1) (ff.add v1 v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v338))))
(assert (= (ff.mul v338 v343) (as ff1 F)))
(assert (= (ff.mul v3 v420) (as ff1 F)))
(assert (= (ff.mul v1 v512) (as ff1 F)))
(assert (= (ff.mul v1 v725) (as ff1 F)))
(assert (= (ff.mul v2 v767) (as ff1 F)))
(assert (= (ff.mul v1 v942) (as ff1 F)))
(assert (= (ff.mul v2 v1024) (as ff1 F)))
(assert (= (ff.mul v2 v1110) (as ff1 F)))

(check-sat)
