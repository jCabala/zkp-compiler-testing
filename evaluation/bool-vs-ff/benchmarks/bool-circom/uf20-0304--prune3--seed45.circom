pragma circom 2.0.6;

include "gates.circom";

include "comparators.circom";

template main_template() {
    signal input x9;
    signal input x14;
    signal input x16;
    (x9 * (1 - x9)) === 0;
    (x14 * (1 - x14)) === 0;
    (x16 * (1 - x16)) === 0;
    component comp_0 = AND();
    comp_0.a <== x9;
    comp_0.b <== x14;
    component comp_1 = IsZero();
    comp_1.in <== comp_0.out;
    component comp_2 = NOT();
    comp_2.in <== comp_1.out;
    comp_2.out === 1;
}

component main = main_template();
