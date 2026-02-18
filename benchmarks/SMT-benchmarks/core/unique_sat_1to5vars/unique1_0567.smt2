; unique_target=0
(set-logic QF_BV)
(declare-fun x1 () Bool)
(assert (not x1))
(check-sat)
(get-model)