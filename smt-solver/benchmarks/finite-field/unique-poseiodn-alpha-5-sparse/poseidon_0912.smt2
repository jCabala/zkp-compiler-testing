; Poseidon-like permutation benchmark (unique SAT)
; prime=CIRCOM (BN254)  t=1  alpha=5  rounds=1
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun x0 () F)

; Output fixed to precomputed value — unique solution exists by bijectivity
(assert (let ((arc_r0_s0 (ff.add x0 (as ff4809459308533083647452408935196092085777758613335235103227009583913854025315 F))))
(let ((sb_r0_s0 (ff.mul (ff.mul (ff.mul (ff.mul arc_r0_s0 arc_r0_s0) arc_r0_s0) arc_r0_s0) arc_r0_s0)))
(let ((mds_r0_s0 (ff.add (ff.mul (as ff1 F) sb_r0_s0))))
(and (= mds_r0_s0 (as ff12875781879931365101993979061095616254302741751130398163632160890477719605460 F)))))))

(check-sat)
