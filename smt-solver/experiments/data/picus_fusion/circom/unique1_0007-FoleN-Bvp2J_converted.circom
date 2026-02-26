pragma circom 2.0.6;

include "../circomlib/comparators.circom";

include "../circomlib/gates.circom";

template main_template() {
    signal input scr1_x1;
    signal input scr1_x2;
    signal input scr1_x3;
    signal input scr2_x1;
    signal output scr1_x3_scr2_x1_fused;
    scr1_x3_scr2_x1_fused <-- ((scr1_x3 + scr2_x1) - (2 * (scr1_x3 * scr2_x1)));
    (scr1_x1 * (1 - scr1_x1)) === 0;
    (scr1_x2 * (1 - scr1_x2)) === 0;
    (scr1_x3 * (1 - scr1_x3)) === 0;
    (scr2_x1 * (1 - scr2_x1)) === 0;
    (scr1_x3_scr2_x1_fused * (1 - scr1_x3_scr2_x1_fused)) === 0;
    component comp_0 = NOT();
    comp_0.in <== scr1_x1;
    component comp_1 = AND();
    comp_1.a <== scr1_x3_scr2_x1_fused;
    comp_1.b <== comp_0.out;
    component comp_2 = AND();
    comp_2.a <== comp_1.out;
    comp_2.b <== scr1_x2;
    component comp_3 = AND();
    comp_3.a <== comp_2.out;
    comp_3.b <== scr2_x1;
    component comp_4 = IsZero();
    comp_4.in <== comp_3.out;
    component comp_5 = NOT();
    comp_5.in <== comp_4.out;
    comp_5.out === 1;
    log("<@> scr1_x3_scr2_x1_fused = ", scr1_x3_scr2_x1_fused);
}

component main = main_template();
