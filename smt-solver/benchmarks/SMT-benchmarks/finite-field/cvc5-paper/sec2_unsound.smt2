(set-logic QF_FF)
(set-option :incremental true)

(define-sort F () (_ FiniteField 394357))

(declare-fun c1 () F)
(declare-fun c2 () F)
(declare-fun c3 () F)
(declare-fun c4 () F)
(declare-fun x () F)
(declare-fun a () F)

(assert (or (= (as ff0 F) c1) (= (as ff1 F) c1)))
(assert (or (= (as ff0 F) c2) (= (as ff1 F) c2)))
(assert (or (= (as ff0 F) c3) (= (as ff1 F) c3)))
(assert (or (= (as ff0 F) c4) (= (as ff1 F) c4)))
(assert (= (ff.mul
            (ff.add (as ff1 F) (ff.neg a))
            (ff.add c1 c2 c3 c4))
           (as ff0 F)))
; (assert (= (ff.mul
;             x
;             (ff.add c1 c2 c3 c4))
;            a))
(assert (not (=
                (= (as ff1 F) a)
                (or
                    (= (as ff1 F) c1)
                    (= (as ff1 F) c2)
                    (= (as ff1 F) c3)
                    (= (as ff1 F) c4)
        ))))

(echo "Expect: sat")
(check-sat)


