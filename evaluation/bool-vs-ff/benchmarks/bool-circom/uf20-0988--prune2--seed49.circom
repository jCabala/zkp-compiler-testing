pragma circom 2.0.6;

include "gates.circom";

include "comparators.circom";

template main_template() {
    signal input x3;
    signal input x12;
    (x3 * (1 - x3)) === 0;
    (x12 * (1 - x12)) === 0;
    component comp_0 = AND();
    comp_0.a <== x12;
    comp_0.b <== x3;
    component comp_1 = IsZero();
    comp_1.in <== comp_0.out;
    component comp_2 = NOT();
    comp_2.in <== comp_1.out;
    comp_2.out === 1;
}

component main = main_template();
