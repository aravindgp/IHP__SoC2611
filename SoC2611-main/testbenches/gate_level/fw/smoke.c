/*
 * SoC2611 firmware smoke suite (runs on the SoC's VexRiscv, bare metal).
 *
 * One UART line per test, dg32-max style:
 *     Tnn name PASS|FAIL key=value ...
 * then  SUMMARY pass=<n> fail=<n>
 * The cocotb side (HW/asic/cocotb/test_fw.py) decodes the UART, drives the
 * push-buttons and the UART RX byte for T05, and checks the LED pattern.
 *
 * Register map: SW/src/soc.h (APB) and SW/base/zta.h (ztachip host regs).
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

/* ztachip host registers: ZTAM_GREG(reg2,reg,vm) = MEM_MAP[(reg2<<5)+reg] */
#define ZTA ((volatile uint32_t *)0x80000000u)
#define REG_DP_READ_SYNC              10
#define REG_DP_READ_INDICATION_AVAIL  12
#define REG_DP_INSTRUCTION_FIFO_AVAIL 14
#define REG_DP_READ_LOG               2    /* register_dp_read_log_c */

#ifndef DP_FIFO_MAX
#define DP_FIFO_MAX 127   /* ztachip_pkg dp_fifo_max_c = 2**dp_instr_fifo_depth_c-1 (63 in the ASIC lean config) */
#endif

extern uint32_t _image_end[];

static int npass, nfail;

static void uart_putc(char c)
{
    while (APB[APB_UART_WRITE_AVAIL] == 0) ;
    APB[APB_UART_WRITE] = (uint32_t)(uint8_t)c;
}
static void uart_puts(const char *s) { while (*s) uart_putc(*s++); }
static void uart_puthex(uint32_t v)
{
    static const char d[] = "0123456789abcdef";
    uart_puts("0x");
    for (int i = 28; i >= 0; i -= 4) uart_putc(d[(v >> i) & 0xf]);
}
static void uart_putdec(uint32_t v)
{
    char b[11]; int i = 10; b[i] = 0;
    do { b[--i] = '0' + (v % 10); v /= 10; } while (v);
    uart_puts(&b[i]);
}
static void result(const char *id, const char *name, int pass)
{
    uart_puts(id); uart_putc(' '); uart_puts(name);
    uart_puts(pass ? " PASS" : " FAIL");
    if (pass) npass++; else nfail++;
}
static void kv(const char *k, uint32_t v) { uart_putc(' '); uart_puts(k); uart_putc('='); uart_puthex(v); }
static void endl(void) { uart_puts("\r\n"); }

/* T01: the accelerator answers on the host bus (AXI -> ztachip host regs) and
 * is in its reset state: instruction FIFO fully available, no indications */
static void t01_ident(void)
{
    uint32_t fifo = ZTA[REG_DP_INSTRUCTION_FIFO_AVAIL];
    uint32_t ind  = ZTA[REG_DP_READ_INDICATION_AVAIL];
    result("T01", "ident", fifo == DP_FIFO_MAX && ind == 0);
    kv("fifo_avail", fifo); kv("ind_avail", ind); endl();
}

/* T02: external memory (DDR model) word / half / byte access with an LFSR
 * pattern and its complement, in the region just above the image */
static void t02_ddr(void)
{
    volatile uint32_t *w = _image_end;
    volatile uint16_t *h = (volatile uint16_t *)_image_end;
    volatile uint8_t  *b = (volatile uint8_t *)_image_end;
    const int N = 256; /* words */
    uint32_t lfsr = 0xACE1u, mism = 0;
    for (int i = 0; i < N; i++) { lfsr = (lfsr >> 1) ^ (-(lfsr & 1u) & 0xB400u) ^ (uint32_t)i << 16; w[i] = lfsr; }
    lfsr = 0xACE1u;
    for (int i = 0; i < N; i++) { lfsr = (lfsr >> 1) ^ (-(lfsr & 1u) & 0xB400u) ^ (uint32_t)i << 16; if (w[i] != lfsr) mism++; }
    for (int i = 0; i < N; i++) w[i] = ~w[i];
    lfsr = 0xACE1u;
    for (int i = 0; i < N; i++) { lfsr = (lfsr >> 1) ^ (-(lfsr & 1u) & 0xB400u) ^ (uint32_t)i << 16; if (w[i] != ~lfsr) mism++; }
    /* sub-word writes through the AXI strobes */
    w[0] = 0x11223344u;
    h[1] = 0xAABBu;            /* upper half */
    b[0] = 0xEEu;              /* lowest byte */
    if (w[0] != 0xAABB33EEu) mism++;
    result("T02", "ddr", mism == 0);
    kv("mismatches", mism); kv("base", (uint32_t)_image_end); endl();
}

/* T03: GPIO - LED walk (checked by cocotb) and push-button read-back
 * (cocotb drives 0x9 on gpio_in) */
static void t03_gpio(void)
{
    static const uint32_t walk[] = {1, 2, 4, 8, 0xA};
    for (unsigned i = 0; i < sizeof walk / sizeof walk[0]; i++) {
        APB[APB_LED] = walk[i];
        for (volatile int d = 0; d < 20; d++) ;
    }
    uint32_t pb = APB[APB_PB] & 0xF;
    result("T03", "gpio", pb == 0x9);
    kv("pb", pb); endl();
}

/* T04: the timer registers advance */
static void t04_timer(void)
{
    uint32_t t0 = APB[APB_TIME_GET], u0 = APB[APB_TIME2_GET], t1 = t0, u1 = u0;
    int i;
    for (i = 0; i < 200000; i++) {
        t1 = APB[APB_TIME_GET]; u1 = APB[APB_TIME2_GET];
        if (t1 != t0 || u1 != u0) break;
    }
    result("T04", "timer", (t1 != t0) || (u1 != u0));
    kv("time", t1); kv("time2", u1); kv("polls", (uint32_t)i); endl();
}

/* T05: UART receive - cocotb sends one byte after seeing the WAIT line */
static void t05_uart_rx(void)
{
    uart_puts("T05 uart_rx WAIT\r\n");
    uint32_t c = 0; int got = 0;
    for (int i = 0; i < 400000 && !got; i++) {
        if (APB[APB_UART_READ_AVAIL]) { c = APB[APB_UART_READ] & 0xFF; got = 1; }
    }
    result("T05", "uart_rx", got && c == 'K');
    kv("byte", c); endl();
}

/* T06: the remaining accelerator read registers answer with their reset
 * values (sync flag clear, log empty) - exercises the host read mux */
static void t06_zta_status(void)
{
    uint32_t sync = ZTA[REG_DP_READ_SYNC];
    uint32_t log  = ZTA[REG_DP_READ_LOG];
    result("T06", "zta_status", sync == 0 && log == 0);
    kv("sync", sync); kv("log", log); endl();
}

int main(void)
{
    APB[APB_LED] = 0x5;
    uart_puts("\r\nSOC2611 FW smoke\r\n");
    t01_ident();
    t02_ddr();
    t03_gpio();
    t04_timer();
    t05_uart_rx();
    t06_zta_status();
    uart_puts("SUMMARY pass="); uart_putdec(npass);
    uart_puts(" fail="); uart_putdec(nfail); endl();
    APB[APB_LED] = nfail ? 0xF : 0x0;
    for (;;) ;
    return 0;
}
