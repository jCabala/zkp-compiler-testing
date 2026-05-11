; Poseidon-like permutation benchmark (unique SAT)
; prime=CIRCOM (BN254)  t=1  alpha=5  rounds=1
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun x0 () F)

; Output fixed to precomputed value — unique solution exists by bijectivity
(assert (let ((arc_r0_s0 (ff.add x0 (as ff21139541321416022742803762624354475106732327951974694043374564530000807031738 F))))
(let ((sb_r0_s0 (ff.mul (ff.mul (ff.mul (ff.mul arc_r0_s0 arc_r0_s0) arc_r0_s0) arc_r0_s0) arc_r0_s0)))
(let ((mds_r0_s0 (ff.mul (as ff1 F) sb_r0_s0)))
(and (= mds_r0_s0 (as ff13143680712268131920296537207772453280079781669954683018996213834488107242003 F)))))))

(check-sat)
