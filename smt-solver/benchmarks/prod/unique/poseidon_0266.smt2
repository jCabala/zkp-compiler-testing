; Poseidon-like permutation benchmark (unique SAT)
; prime=CIRCOM (BN254)  t=1  alpha=5  rounds=1
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun x0 () F)

; Output fixed to precomputed value — unique solution exists by bijectivity
(assert (let ((arc_r0_s0 (ff.add x0 (as ff13751817964065111641850774243763857645658918762348634836518523605704778101085 F))))
(let ((sb_r0_s0 (ff.mul (ff.mul (ff.mul (ff.mul arc_r0_s0 arc_r0_s0) arc_r0_s0) arc_r0_s0) arc_r0_s0)))
(let ((mds_r0_s0 (ff.add (ff.mul (as ff1 F) sb_r0_s0))))
(and (= mds_r0_s0 (as ff13042727424757738344937386829886719387506685550049286331683707288527857072062 F)))))))

(check-sat)
