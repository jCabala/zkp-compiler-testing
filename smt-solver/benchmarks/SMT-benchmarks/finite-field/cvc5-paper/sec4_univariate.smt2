(set-logic QF_FF)
(set-option :incremental true)

(define-sort F () (_ FiniteField 101))

(declare-fun x () F)

(assert (= (ff.mul x x) (as ff2 F)))

(echo "Expect: unsat")
(check-sat)
