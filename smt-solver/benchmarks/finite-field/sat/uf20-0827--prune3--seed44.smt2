; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0827--prune3--seed44.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=13 nConstraints=12
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v3 () F)
(declare-fun v212 () F)
(declare-fun v284 () F)
(declare-fun v341 () F)
(declare-fun v407 () F)
(declare-fun v570 () F)
(declare-fun v610 () F)
(declare-fun v628 () F)
(declare-fun v688 () F)
(declare-fun v982 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v3 (ff.add v3 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v3) (as ff0 F)))
(assert (= (ff.mul v3 v212) (as ff1 F)))
(assert (= (ff.mul v2 v1) (ff.add v1 v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v284))))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v341) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v407) (as ff1 F)))
(assert (= (ff.mul v284 v570) (as ff1 F)))
(assert (= (ff.mul v1 v610) (as ff1 F)))
(assert (= (ff.mul v3 v1) (ff.add v1 v3 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v628))))
(assert (= (ff.mul v628 v688) (as ff1 F)))
(assert (= (ff.mul v3 v982) (as ff1 F)))

(check-sat)
