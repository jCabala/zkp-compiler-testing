(set-logic QF_LIA)
(declare-fun x () Int)
(assert (let ((t (+ x 1))) (> t 0)))
(check-sat)