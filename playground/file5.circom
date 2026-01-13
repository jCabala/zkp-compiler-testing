pragma circom 2.0.6;

include "../circomlib/comparators.circom";

include "../circomlib/gates.circom";

template main_template() {
    signal input f_g_z;
    signal input g_z;
    signal input z;
    component comp_0 = IsEqual();
    comp_0.in[0] <== f_g_z;
    comp_0.in[1] <== z;
    comp_0.out === 1;
    component comp_1 = IsEqual();
    comp_1.in[0] <== g_z;
    comp_1.in[1] <== z;
    component comp_2 = NOT();
    comp_2.in <== comp_1.out;
    comp_2.out === 1;
}

component main = main_template();
