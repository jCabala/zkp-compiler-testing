pragma circom 2.0.6;

include "../circomlib/gates.circom";

template main_template() {
    signal input scr1_a;
    signal input scr2_a;
    component comp_0 = NOT();
    comp_0.in <== scr1_a;
    component comp_1 = AND();
    comp_1.a <== scr1_a;
    comp_1.b <== comp_0.out;
    component comp_2 = NOT();
    comp_2.in <== scr2_a;
    component comp_3 = AND();
    comp_3.a <== scr2_a;
    comp_3.b <== comp_2.out;
    component comp_4 = OR();
    comp_4.a <== comp_1.out;
    comp_4.b <== comp_3.out;
    comp_4.out === 1;
}

component main = main_template();
