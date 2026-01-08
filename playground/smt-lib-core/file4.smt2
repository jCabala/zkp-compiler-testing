; Core theory example 4: booleans only
(declare-fun u () Bool)
(declare-fun v () Bool)
(declare-fun huv () Bool)
(assert huv)
(assert (or (not huv) v))
(assert u)
(check-sat)
(get-model)
