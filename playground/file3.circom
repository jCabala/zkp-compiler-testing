pragma circom 2.0.6;

include "../circomlib/comparators.circom";

include "../circomlib/gates.circom";

template main_template() {
    signal input c;
    signal input d;
    signal input p_c;
    signal input p_d;
    p_c === 1;
    component comp_0 = NOT();
    comp_0.in <== p_d;
    comp_0.out === 1;
    component comp_1 = IsEqual();
    comp_1.in[0] <== c;
    comp_1.in[1] <== d;
    component comp_2 = NOT();
    comp_2.in <== comp_1.out;
    comp_2.out === 1;
}

component main = main_template();
