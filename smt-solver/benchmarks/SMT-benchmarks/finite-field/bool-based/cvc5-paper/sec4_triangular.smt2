(set-logic QF_FF)
(set-option :incremental true)

(define-sort F () (_ FiniteField 394357))

(declare-fun x1 () F)
(declare-fun x2 () F)
(declare-fun x3 () F)
(declare-fun x4 () F)
(declare-fun x5 () F)

(assert (= (as ff0 F)
    (ff.add x1 x2 x3 x4 x5)
))
(assert (= (as ff0 F)
    (ff.add
        (ff.mul x1 x2)
        (ff.mul x2 x3)
        (ff.mul x3 x4)
        (ff.mul x4 x5)
        (ff.mul x5 x1)
    )
))
(assert (= (as ff0 F)
    (ff.add
        (ff.mul x1 x2 x3)
        (ff.mul x2 x3 x4)
        (ff.mul x3 x4 x5)
        (ff.mul x4 x5 x1)
        (ff.mul x5 x1 x2)
    )
))
(assert (= (as ff0 F)
    (ff.add
        (ff.mul x1 x2 x3 x4)
        (ff.mul x2 x3 x4 x5)
        (ff.mul x3 x4 x5 x1)
        (ff.mul x4 x5 x1 x2)
        (ff.mul x5 x1 x2 x3)
    )
))
(assert (= (as ff1 F)
    (ff.mul x1 x2 x3 x4 x5)
))

(echo "Expect: unsat")
(check-sat)


