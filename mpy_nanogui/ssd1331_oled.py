# Customise for your hardware config
# SSD-1331 display on SPI0

from machine import Pin, SPI
import gc

# Uses SPI port 0
spi_port = 0
PIN_MISO = 16
PIN_CS = 17
PIN_SCLK = 18
PIN_MOSI = 19
PIN_RST = 20
PIN_DC = 21

from drivers.ssd1331.ssd1331 import SSD1331 as SSD

pin_cs = Pin(PIN_CS, Pin.OUT, value=1)
pin_dc = Pin(PIN_DC, Pin.OUT, value=0)
pin_rst = Pin(PIN_RST, Pin.OUT, value=1)
# using hardware SPI0
# The bus speed is limited to some values like 12 or 24 MHz by the microcontroller
# The SSD1331 datasheet states a minimum clock cycle time of 150 ns (6MHz)
# 24 MHz works without problems, so far
# transmission of a full frame buffer takes just over 4ms in that case
spi = SPI(
    spi_port,
    baudrate=24_000_000,
    mosi=Pin(PIN_MOSI),
    sck=Pin(PIN_SCLK))
print(spi)
gc.collect()  # Precaution before instantiating framebuf
oled = SSD(spi, pin_cs, pin_dc, pin_rst)
