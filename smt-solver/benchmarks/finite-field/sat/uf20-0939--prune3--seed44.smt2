; Auto-generated finite-field SMT-LIB (QF_FF)
; source=/home/jcabala/fyp/new_repos/zkp_testing/smt-solver/benchmarks/core/sat/uf20-0939--prune3--seed44.smt2
; backend=circom
; prime=21888242871839275222246405745257275088548364400416034343698204186575808495617
; nVars=14 nConstraints=13
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun v1 () F)
(declare-fun v2 () F)
(declare-fun v3 () F)
(declare-fun v180 () F)
(declare-fun v185 () F)
(declare-fun v240 () F)
(declare-fun v248 () F)
(declare-fun v312 () F)
(declare-fun v380 () F)
(declare-fun v390 () F)
(declare-fun v395 () F)
(declare-fun v714 () F)
(declare-fun v853 () F)

(assert (= (ff.mul v1 (ff.add v1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v2 (ff.add v2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul v3 (ff.add v3 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v1)) v1) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v2) (as ff0 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v3) (as ff0 F)))
(assert (= (ff.mul v2 v1) (ff.add v1 v2 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v180))))
(assert (= (ff.mul v180 v185) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v3) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2) v3 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v240))))
(assert (= (ff.mul v240 v248) (as ff1 F)))
(assert (= (ff.mul v3 v1) (ff.add v1 v3 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v312))))
(assert (= (ff.mul v1 v380) (as ff1 F)))
(assert (= (ff.mul v3 (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2))) (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2) v3 (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v390))))
(assert (= (ff.mul v390 v395) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v3)) v714) (as ff1 F)))
(assert (= (ff.mul (ff.add (as ff1 F) (ff.mul (as ff21888242871839275222246405745257275088548364400416034343698204186575808495616 F) v2)) v853) (as ff1 F)))

(check-sat)
