/*
 * Camera capture test (runs on the SoC's VexRiscv, bare metal), 13 November 2026.
 *
 * What it proves, pad to pad: a frame on the camera pads goes through the camera block (two bytes per pixel in,
 * three bytes per pixel out), the clock crossing FIFO and the stream writer into the external memory, and the
 * CPU reads it back from there and prints a checksum on the UART.
 *
 * The testbench (HW/asic/signoff/gl_sim/tb_chip_gl.sv with CAM_FRAMES > 0) sends frames of CAM_H rows of 640
 * pixels with a known byte pattern, again and again. The camera block starts at the first VSYNC after its own
 * I2C set-up of the camera has finished (about 721,000 camera clock cycles after reset) and the stream is enabled.
 * The stream writer writes bursts of 256 bytes. This program waits until burst number CAM_BURSTS has arrived and
 * then sums the bursts before it. The expected sum, -DCAM_EXPECT, is calculated by gl_sim/cam_expect.py from the
 * same pattern and the pixel packing of HW/src/soc/peripherals/camera.vhd.
 *
 * Output, in the style of smoke.c:   T07 camera PASS|FAIL sum=0x... exp=0x... w0=0x... polls=0x...
 *                                    SUMMARY pass=<n> fail=<n>
 */
#include <stdint.h>

#define APB ((volatile uint32_t *)0xC0000000u)
#define APB_LED              0
#define APB_CAMERA_ENABLE    3
#define APB_CAMERA_CURR      4
#define APB_CAMERA_BUFFER    5
#define APB_UART_WRITE       16
#define APB_UART_WRITE_AVAIL 18

#ifndef CAM_EXPECT
#define CAM_EXPECT 0u
#endif
#ifndef CAM_BURSTS
#define CAM_BURSTS 28              /* bursts of 256 bytes that are summed */
#endif
#define CAM_BUF   0x00040000u      /* frame buffer in the external memory, above the image and its stack */
#define FLUSH_DATA_CACHE() __asm__ volatile(".word 0x500F")

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
static void kv(const char *k, uint32_t v) { uart_putc(' '); uart_puts(k); uart_putc('='); uart_puthex(v); }

int main(void)
{
    volatile uint32_t *buf = (volatile uint32_t *)CAM_BUF;
    volatile uint32_t *mark = buf + (CAM_BURSTS * 256) / 4;     /* first word of the burst after the summed ones */
    uint32_t sum = 0, polls = 0;
    int got = 0;

    APB[APB_LED] = 0x5;
#ifdef CAM_VERBOSE
    uart_puts("\r\nSOC2611 FW capture\r\n");
#endif

    *mark = 0xFFFFFFFFu;            /* camera bytes have a zero low nibble, so this value cannot come from a frame */
    for (int r = 0; r < 4; r++) APB[APB_CAMERA_BUFFER + r] = CAM_BUF;
    APB[APB_CAMERA_ENABLE] = 1;
    APB[APB_LED] = 0x6;

    for (polls = 0; polls < 4000000u && !got; polls++) {
        FLUSH_DATA_CACHE();         /* the stream writer writes behind the data cache */
        if (*mark != 0xFFFFFFFFu) got = 1;
    }
    APB[APB_LED] = 0x7;
    FLUSH_DATA_CACHE();
    for (unsigned i = 0; i < (CAM_BURSTS * 256u) / 4u; i++) {
        uint32_t w = buf[i];
        sum = ((sum << 1) | (sum >> 31)) ^ w;
    }
#ifdef CAM_VERBOSE
    uart_puts("T07 camera");
    uart_puts((got && sum == CAM_EXPECT) ? " PASS" : " FAIL");
    kv("sum", sum); kv("exp", CAM_EXPECT); kv("w0", buf[0]); kv("polls", polls);
    uart_puts("\r\n");
    uart_puts((got && sum == CAM_EXPECT) ? "SUMMARY pass=1 fail=0\r\n" : "SUMMARY pass=0 fail=1\r\n");
#else
    /* short form: C, the eight hex digits of the sum, then P1F0 or P0F1 (one character costs 21,700 clock cycles) */
    uart_putc('C');
    for (int i = 28; i >= 0; i -= 4) uart_putc("0123456789abcdef"[(sum >> i) & 0xf]);
    uart_putc('\n');
    uart_puts((got && sum == CAM_EXPECT) ? "P1F0\n" : "P0F1\n");
#endif
    APB[APB_LED] = (got && sum == CAM_EXPECT) ? 0x0 : 0xF;
    for (;;) ;
    return 0;
}
