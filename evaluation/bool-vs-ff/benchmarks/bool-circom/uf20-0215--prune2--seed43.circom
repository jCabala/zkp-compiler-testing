pragma circom 2.0.6;

include "gates.circom";

include "comparators.circom";

template main_template() {
    signal input x2;
    signal input x10;
    (x2 * (1 - x2)) === 0;
    (x10 * (1 - x10)) === 0;
    component comp_0 = NOT();
    comp_0.in <== x2;
    component comp_1 = NOT();
    comp_1.in <== x10;
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
