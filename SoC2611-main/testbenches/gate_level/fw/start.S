/*
 * Minimal bare-metal start-up for the SoC2611 firmware tests.
 * The VexRiscv in soc_base boots at 0x00004000 (see HW/riscv/sim/riscv.vhd),
 * which link.ld places this code at. No interrupts, no libc.
 */
    .section .start, "ax", @progbits
    .global _start
_start:
    la      sp, _stack_top
    /* zero .bss */
    la      t0, _bss_start
    la      t1, _bss_end
1:  bgeu    t0, t1, 2f
    sw      zero, 0(t0)
    addi    t0, t0, 4
    j       1b
2:  call    main
3:  j       3b
