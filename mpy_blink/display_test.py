# spi = SPI(0, baudrate=400000)           # Create SPI peripheral 0 at frequency of 400kHz.
# SPI.init(baudrate=1000000, *, polarity=0, phase=0, bits=8, firstbit=SPI.MSB, sck=None, mosi=None, miso=None, pins=(SCK, MOSI, MISO))
# SPI0 sck=pin4, mosi=pin1, cs=pin2, mosi=pin5, cs=pin2, d/c=pin7)
# cs = Pin(2, mode=Pin.OUT, value=1)      # Create chip-select
# dc = Pin(7, mode=Pin.OUT, value=1)      # Create chip-select

# Demo for SSD1331
from machine import Pin, SPI
import ssd1331
import time

# Uses SPI port 0
spi_port = 0
MISO = 16
CS = 17
SCLK = 18
MOSI = 19
RST = 20
DC = 21

spi = SPI(
    spi_port,
    baudrate=400000,
    mosi=Pin(MOSI),
    sck=Pin(SCLK))
print(spi)

oled = ssd1331.SSD1331(
    spi,
    dc=Pin(DC),
    res=Pin(RST),
    cs=Pin(CS))
print(oled)

# display initialization is performed automatically

# Add some text
oled.text("This is red", 5, 3, ssd1331.DISPLAY_RED)
oled.text('cyan', 5, 13, ssd1331.DISPLAY_DARK_RED)
oled.text("Which is blue", 5, 23, ssd1331.DISPLAY_BLUE)
oled.text('and green', 5, 33, ssd1331.DISPLAY_GREEN)
oled.text('Up to 6 lines -', 5, 43, ssd1331.DISPLAY_YELLOW)
oled.text("dark blue", 5, 53, ssd1331.DISPLAY_DARK_BLUE)

# Finally update the oled display so the text is displayed
oled.show()
