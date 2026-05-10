; Poseidon-like permutation benchmark (unique SAT)
; prime=CIRCOM (BN254)  t=1  alpha=5  rounds=1
(set-logic QF_FF)

(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))

(declare-fun x0 () F)

; Output fixed to precomputed value — unique solution exists by bijectivity
(assert (let ((arc_r0_s0 (ff.add x0 (as ff5007603548327883620810847508542642191858056855399235866923355830424568086103 F))))
(let ((sb_r0_s0 (ff.mul (ff.mul (ff.mul (ff.mul arc_r0_s0 arc_r0_s0) arc_r0_s0) arc_r0_s0) arc_r0_s0)))
(let ((mds_r0_s0 (ff.mul (as ff1 F) sb_r0_s0)))
(and (= mds_r0_s0 (as ff4824628068523054694464864743005877527967193248176296943846933637571106788309 F)))))))

(check-sat)
