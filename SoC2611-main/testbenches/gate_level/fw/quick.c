/*
 * Quick version of the firmware smoke suite (smoke.c) for slow simulators, 13 November 2026.
 * The same six checks, but almost no text: one UART character costs 21,700 input clock cycles on this chip
 * (1085 system clock cycles per bit), and the full suite prints about 340 of them.
 *
 * Output:   W            the firmware waits for one byte on the UART (the testbench sends 'K')
 *           Q<hh>        hh = bit mask of the checks that passed, bit 0 = T01 ... bit 5 = T06 (3f = all six)
 *           P<n>F<m>     number of checks passed and failed, the summary line of the testbench
 * LEDs as in smoke.c: 5 after boot, the walk 1 2 4 8 a, then 0 (no failure) or f.
 */
#include <stdint.h>

#define APB ((volatile uint32_t *)0xC0000000u)
#define APB_LED              0
#define APB_PB               2
#define APB_UART_READ        15
#define APB_UART_WRITE       16
#define APB_UART_READ_AVAIL  17
#define APB_UART_WRITE_AVAIL 18
#define APB_TIME_GET         19
#define APB_TIME2_GET        20
#define ZTA ((volatile uint32_t *)0x80000000u)
#define REG_DP_READ_SYNC              10
#define REG_DP_READ_INDICATION_AVAIL  12
#define REG_DP_INSTRUCTION_FIFO_AVAIL 14
#define REG_DP_READ_LOG               2
#ifndef DP_FIFO_MAX
#define DP_FIFO_MAX 63
#endif

extern uint32_t _image_end[];

static void uart_putc(char c)
{
    while (APB[APB_UART_WRITE_AVAIL] == 0) ;
    APB[APB_UART_WRITE] = (uint32_t)(uint8_t)c;
}
static char hex1(uint32_t v) { return "0123456789abcdef"[v & 0xf]; }

int main(void)
{
    uint32_t mask = 0;
    APB[APB_LED] = 0x5;

    /* T01: the accelerator answers on the host bus and is in its reset state */
    if (ZTA[REG_DP_INSTRUCTION_FIFO_AVAIL] == DP_FIFO_MAX && ZTA[REG_DP_READ_INDICATION_AVAIL] == 0) mask |= 1;

    /* T02: external memory, word / half / byte, just above the image (64 words here, 256 in smoke.c) */
    {
        volatile uint32_t *w = _image_end;
        volatile uint16_t *h = (volatile uint16_t *)_image_end;
        volatile uint8_t  *b = (volatile uint8_t *)_image_end;
        const int N = 64;
        uint32_t lfsr = 0xACE1u, mism = 0;
        for (int i = 0; i < N; i++) { lfsr = (lfsr >> 1) ^ (-(lfsr & 1u) & 0xB400u) ^ (uint32_t)i << 16; w[i] = lfsr; }
        lfsr = 0xACE1u;
        for (int i = 0; i < N; i++) { lfsr = (lfsr >> 1) ^ (-(lfsr & 1u) & 0xB400u) ^ (uint32_t)i << 16; if (w[i] != lfsr) mism++; }
        for (int i = 0; i < N; i++) w[i] = ~w[i];
        lfsr = 0xACE1u;
        for (int i = 0; i < N; i++) { lfsr = (lfsr >> 1) ^ (-(lfsr & 1u) & 0xB400u) ^ (uint32_t)i << 16; if (w[i] != ~lfsr) mism++; }
        w[0] = 0x11223344u; h[1] = 0xAABBu; b[0] = 0xEEu;
        if (w[0] != 0xAABB33EEu) mism++;
        if (mism == 0) mask |= 2;
    }

    /* T03: LED walk and the button pads (the testbench drives 9) */
    {
        static const uint32_t walk[] = {1, 2, 4, 8, 0xA};
        for (unsigned i = 0; i < sizeof walk / sizeof walk[0]; i++) {
            APB[APB_LED] = walk[i];
            for (volatile int d = 0; d < 20; d++) ;
        }
        if ((APB[APB_PB] & 0xF) == 0x9) mask |= 4;
    }

    /* T04: a timer register advances */
    {
        uint32_t t0 = APB[APB_TIME_GET], u0 = APB[APB_TIME2_GET];
        for (int i = 0; i < 200000; i++)
            if (APB[APB_TIME_GET] != t0 || APB[APB_TIME2_GET] != u0) { mask |= 8; break; }
    }

    /* T05: UART receive */
    {
        uint32_t c = 0; int got = 0;
        uart_putc('W'); uart_putc('\n');
        for (int i = 0; i < 400000 && !got; i++)
            if (APB[APB_UART_READ_AVAIL]) { c = APB[APB_UART_READ] & 0xFF; got = 1; }
        if (got && c == 'K') mask |= 16;
    }

    /* T06: the other accelerator read registers answer with their reset values */
    if (ZTA[REG_DP_READ_SYNC] == 0 && ZTA[REG_DP_READ_LOG] == 0) mask |= 32;

    {
        int np = 0;
        for (int i = 0; i < 6; i++) np += (mask >> i) & 1;
        uart_putc('Q'); uart_putc(hex1(mask >> 4)); uart_putc(hex1(mask)); uart_putc('\n');
        uart_putc('P'); uart_putc((char)('0' + np)); uart_putc('F'); uart_putc((char)('0' + 6 - np)); uart_putc('\n');
        APB[APB_LED] = (np == 6) ? 0x0 : 0xF;
    }
    for (;;) ;
    return 0;
}
