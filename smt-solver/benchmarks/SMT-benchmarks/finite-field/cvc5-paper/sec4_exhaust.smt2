(set-logic QF_FF)
(set-option :incremental true)

(define-sort F () (_ FiniteField 394357))

(declare-fun x1 () F)
(declare-fun x2 () F)

(assert (= (as ff0 F) (ff.add x1 x2)))

(echo "Expect: sat")
(check-sat)

