pragma circom 2.0.6;

include "gates.circom";

include "comparators.circom";

template main_template() {
    signal input x14;
    signal input x17;
    signal input x18;
    (x14 * (1 - x14)) === 0;
    (x17 * (1 - x17)) === 0;
    (x18 * (1 - x18)) === 0;
    component comp_0 = NOT();
    comp_0.in <== x18;
    component comp_1 = NOT();
    comp_1.in <== x17;
    component comp_2 = AND();
    comp_2.a <== comp_0.out;
    comp_2.b <== comp_1.out;
    component comp_3 = IsZero();
    comp_3.in <== comp_2.out;
    component comp_4 = NOT();
    comp_4.in <== comp_3.out;
    comp_4.out === 1;
}

component main = main_template();
