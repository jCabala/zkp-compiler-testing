pragma circom 2.0.6;

include "../circomlib/gates.circom";

include "../circomlib/comparators.circom";

template main_template() {
    signal input scr1_x1;
    signal input scr2_x2;
    signal output scr1_x1_scr2_x2_fused;
    scr1_x1_scr2_x2_fused <-- ((scr1_x1 + scr2_x2) - (2 * (scr1_x1 * scr2_x2)));
    (scr1_x1 * (1 - scr1_x1)) === 0;
    (scr2_x2 * (1 - scr2_x2)) === 0;
    (scr1_x1_scr2_x2_fused * (1 - scr1_x1_scr2_x2_fused)) === 0;
    component comp_0 = OR();
    comp_0.a <== scr1_x1;
    comp_0.b <== scr2_x2;
    component comp_1 = IsZero();
    comp_1.in <== comp_0.out;
    component comp_2 = NOT();
    comp_2.in <== comp_1.out;
    comp_2.out === 1;
    log("<@> scr1_x1_scr2_x2_fused = ", scr1_x1_scr2_x2_fused);
}

component main = main_template();
