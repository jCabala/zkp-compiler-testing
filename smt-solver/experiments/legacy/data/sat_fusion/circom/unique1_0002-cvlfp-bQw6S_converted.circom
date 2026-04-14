pragma circom 2.0.6;

include "../circomlib/gates.circom";

include "../circomlib/comparators.circom";

template main_template() {
    signal input scr1_x1;
    signal input scr1_x2;
    signal input scr2_x1;
    signal output scr1_x1_scr2_x1_fused;
    scr1_x1_scr2_x1_fused <-- ((scr1_x1 + scr2_x1) - (2 * (scr1_x1 * scr2_x1)));
    (scr1_x1 * (1 - scr1_x1)) === 0;
    (scr1_x2 * (1 - scr1_x2)) === 0;
    (scr2_x1 * (1 - scr2_x1)) === 0;
    (scr1_x1_scr2_x1_fused * (1 - scr1_x1_scr2_x1_fused)) === 0;
    component comp_0 = IsEqual();
    comp_0.in[0] <== scr1_x1_scr2_x1_fused;
    comp_0.in[1] <== scr2_x1;
    component comp_1 = AND();
    comp_1.a <== scr1_x2;
    comp_1.b <== comp_0.out;
    component comp_2 = IsEqual();
    comp_2.in[0] <== scr1_x1_scr2_x1_fused;
    comp_2.in[1] <== scr1_x1;
    component comp_3 = AND();
    comp_3.a <== comp_1.out;
    comp_3.b <== comp_2.out;
    component comp_4 = IsZero();
    comp_4.in <== comp_3.out;
    component comp_5 = NOT();
    comp_5.in <== comp_4.out;
    comp_5.out === 1;
    log("<@> scr1_x1_scr2_x1_fused = ", scr1_x1_scr2_x1_fused);
}

component main = main_template();
