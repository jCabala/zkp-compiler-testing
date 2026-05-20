pragma circom 2.0.6;

include "gates.circom";

include "comparators.circom";

template main_template() {
    signal input x8;
    signal input x17;
    (x8 * (1 - x8)) === 0;
    (x17 * (1 - x17)) === 0;
    component comp_0 = AND();
    comp_0.a <== x8;
    comp_0.b <== x17;
    component comp_1 = IsZero();
    comp_1.in <== comp_0.out;
    component comp_2 = NOT();
    comp_2.in <== comp_1.out;
    comp_2.out === 1;
}

component main = main_template();
