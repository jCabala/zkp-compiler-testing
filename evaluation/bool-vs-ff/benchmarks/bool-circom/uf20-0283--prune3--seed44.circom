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
    component comp_0 = AND();
    comp_0.a <== x14;
    comp_0.b <== x18;
    component comp_1 = AND();
    comp_1.a <== comp_0.out;
    comp_1.b <== x17;
    component comp_2 = IsZero();
    comp_2.in <== comp_1.out;
    component comp_3 = NOT();
    comp_3.in <== comp_2.out;
    comp_3.out === 1;
}

component main = main_template();
