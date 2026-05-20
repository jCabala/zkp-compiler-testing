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
    comp_0.in <== x17;
    component comp_1 = NOT();
    comp_1.in <== x18;
    component comp_2 = AND();
    comp_2.a <== comp_0.out;
    comp_2.b <== comp_1.out;
    component comp_3 = AND();
    comp_3.a <== comp_2.out;
    comp_3.b <== x14;
    component comp_4 = IsZero();
    comp_4.in <== comp_3.out;
    component comp_5 = NOT();
    comp_5.in <== comp_4.out;
    comp_5.out === 1;
}

component main = main_template();
