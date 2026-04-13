(set-logic QF_FF)
(define-sort F () (_ FiniteField 101))
(declare-fun scr1_x1 () F)
(declare-fun scr2_x2 () F)
(declare-fun scr1_x1_scr2_x2_fused () F)
; Booleanity constraints
(assert (= (ff.mul scr1_x1 (ff.add scr1_x1 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul scr2_x2 (ff.add scr2_x2 (ff.neg (as ff1 F)))) (as ff0 F)))
(assert (= (ff.mul scr1_x1_scr2_x2_fused (ff.add scr1_x1_scr2_x2_fused (ff.neg (as ff1 F)))) (as ff0 F)))
; scr1_x1 = 1, scr2_x2 = 1 (same as (and scr1_x1 scr2_x2))
(assert (= scr1_x1 (as ff1 F)))
(assert (= scr2_x2 (as ff1 F)))
; XOR in field: x + y - 2xy
(assert (= scr1_x1_scr2_x2_fused
           (ff.add scr1_x1
                   scr2_x2
                   (ff.neg (ff.mul (as ff2 F) (ff.mul scr1_x1 scr2_x2))))))
(check-sat)
