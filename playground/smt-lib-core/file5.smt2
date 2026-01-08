; Core theory example 5: boolean composition
(declare-fun f_g_z () Bool)
(declare-fun g_z () Bool)
(declare-fun z () Bool)
(assert (= f_g_z z))
(assert (not (= g_z z)))
(check-sat)
(get-model)
; end
