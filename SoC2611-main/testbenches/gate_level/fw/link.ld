/* SoC2611 firmware test image: lives in external DDR (mem128 model in
 * simulation), entry at the CPU reset vector 0x00004000. */
OUTPUT_FORMAT("elf32-littleriscv")
OUTPUT_ARCH(riscv)
ENTRY(_start)

MEMORY {
  DDR (rwx) : ORIGIN = 0x00004000, LENGTH = 112K
}

_stack_size = 4K;

SECTIONS {
  .text : {
    KEEP(*(.start))
    *(.text*)
    *(.rodata*)
    . = ALIGN(16);
  } > DDR

  .data : {
    *(.data*)
    *(.sdata*)
    . = ALIGN(16);
  } > DDR

  .bss (NOLOAD) : {
    _bss_start = .;
    *(.bss*)
    *(.sbss*)
    *(COMMON)
    . = ALIGN(16);
    _bss_end = .;
  } > DDR

  /* stack right above .bss, then the scratch region the memory test uses */
  . = ALIGN(16);
  _stack_bottom = .;
  . = . + _stack_size;
  _stack_top = .;
  _image_end = .;
}
