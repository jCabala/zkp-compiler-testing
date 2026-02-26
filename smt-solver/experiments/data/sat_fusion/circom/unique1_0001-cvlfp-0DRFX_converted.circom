pragma circom 2.0.6;

include "../circomlib/gates.circom";

include "../circomlib/comparators.circom";

template main_template() {
    signal input scr1_x1;
    signal input scr2_x1;
    signal output scr1_x1_scr2_x1_fused;
    scr1_x1_scr2_x1_fused <-- ((scr1_x1 + scr2_x1) - (2 * (scr1_x1 * scr2_x1)));
    (scr1_x1 * (1 - scr1_x1)) === 0;
    (scr2_x1 * (1 - scr2_x1)) === 0;
    (scr1_x1_scr2_x1_fused * (1 - scr1_x1_scr2_x1_fused)) === 0;
    component comp_0 = NOT();
    comp_0.in <== scr1_x1;
    component comp_1 = NOT();
    comp_1.in <== scr1_x1_scr2_x1_fused;
    component comp_2 = AND();
    comp_2.a <== comp_0.out;
    comp_2.b <== comp_1.out;
    component comp_3 = IsZero();
    comp_3.in <== comp_2.out;
    component comp_4 = NOT();
    comp_4.in <== comp_3.out;
    comp_4.out === 1;
    log("<@> scr1_x1_scr2_x1_fused = ", scr1_x1_scr2_x1_fused);
}

component main = main_template();
