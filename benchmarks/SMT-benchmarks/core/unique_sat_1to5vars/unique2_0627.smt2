; unique_target=01
(set-logic QF_BV)
(declare-fun x1 () Bool)
(declare-fun x2 () Bool)
(assert (or x2 (not x1)))
(assert (or x2 x1))
(assert (or (not x1) (not x2)))
(check-sat)
(get-model)