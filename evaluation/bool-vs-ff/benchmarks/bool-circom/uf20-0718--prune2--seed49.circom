pragma circom 2.0.6;

include "gates.circom";

include "comparators.circom";

template main_template() {
    signal input x3;
    signal input x12;
    (x3 * (1 - x3)) === 0;
    (x12 * (1 - x12)) === 0;
    component comp_0 = IsZero();
    comp_0.in <== x12;
    component comp_1 = NOT();
    comp_1.in <== comp_0.out;
    comp_1.out === 1;
}

component main = main_template();
