pragma circom 2.0.6;

include "gates.circom";

include "comparators.circom";

template main_template() {
    signal input x3;
    signal input x13;
    (x3 * (1 - x3)) === 0;
    (x13 * (1 - x13)) === 0;
    component comp_0 = NOT();
    comp_0.in <== x13;
    component comp_1 = IsZero();
    comp_1.in <== comp_0.out;
    component comp_2 = NOT();
    comp_2.in <== comp_1.out;
    comp_2.out === 1;
}

component main = main_template();
