# MicroPython SSD1331 OLED driver, SPI interface

from micropython import const
import framebuf
import time

# display definitions
WIDTH = const(96)
HEIGHT = const(64)
SPI_RATE = 400000

# color definitions
# 5 MSB -> blue  : mask 0xF800
# 6 bit -> red   : mask 0x07E0
# 5 LSB -> green : mask 0x001F
# effective color depth seems to be just 2 bits
DISPLAY_BLACK =         0x0000
DISPLAY_BLUE =          0xF800
DISPLAY_DARK_BLUE =     0x0800
DISPLAY_RED =           0x07E0
DISPLAY_DARK_RED =      0x0060
DISPLAY_GREEN =         0x001F
DISPLAY_CYAN =          0xF81F
DISPLAY_MAGENTA =       0xFFE0
DISPLAY_YELLOW =        0x07FF
DISPLAY_WHITE =         0xFFFF

# command and register definitions
DISABLE_FILL                    = const(0x00)
ENABLE_FILL                     = const(0x01)
SET_COLUMN_ADDRESS              = const(0x15)
DRAW_LINE                       = const(0x21)
DRAW_RECTANGLE                  = const(0x22)
COPY_WINDOW                     = const(0x23)
DIM_WINDOW                      = const(0x24)
CLEAR_WINDOW                    = const(0x25)
FILL_WINDOW                     = const(0x26)
CONTINUOUS_SCROLLING_SETUP      = const(0x27)
DEACTIVE_SCROLLING              = const(0x2E)
ACTIVE_SCROLLING                = const(0x2F)
SET_ROW_ADDRESS                 = const(0x75)

SET_CONTRAST_A                  = const(0x81)
SET_CONTRAST_B                  = const(0x82)
SET_CONTRAST_C                  = const(0x83)
MASTER_CURRENT_CONTROL          = const(0x87)
SET_PRECHARGE_SPEED_A           = const(0x8A)
SET_PRECHARGE_SPEED_B           = const(0x8B)
SET_PRECHARGE_SPEED_C           = const(0x8C)
SET_REMAP                       = const(0xA0)
SET_DISPLAY_START_LINE          = const(0xA1)
SET_DISPLAY_OFFSET              = const(0xA2)
NORMAL_DISPLAY                  = const(0xA4)
ENTIRE_DISPLAY_ON               = const(0xA5)
ENTIRE_DISPLAY_OFF              = const(0xA6)
INVERSE_DISPLAY                 = const(0xA7)
SET_MULTIPLEX_RATIO             = const(0xA8)
DIM_MODE_SETTING                = const(0xAB)
SET_MASTER_CONFIGURE            = const(0xAD)
DIM_MODE_DISPLAY_ON             = const(0xAC)
DISPLAY_OFF                     = const(0xAE)
NORMAL_BRIGHTNESS_DISPLAY_ON    = const(0xAF)
POWER_SAVE_MODE                 = const(0xB0)
PHASE_PERIOD_ADJUSTMENT         = const(0xB1)
DISPLAY_CLOCK_DIV               = const(0xB3)
SET_GRAy_SCALE_TABLE            = const(0xB8)
ENABLE_LINEAR_GRAY_SCALE_TABLE  = const(0xB9)
SET_PRECHARGE_VOLTAGE           = const(0xBB)
SET_V_VOLTAGE                   = const(0xBE)

# Subclassing FrameBuffer provides support for graphics primitives
# http://docs.micropython.org/en/latest/pyboard/library/framebuf.html

class SSD1331(framebuf.FrameBuffer):
    def __init__(self, spi, dc, res, cs):
        """
        Create display connected to an spi interface.
        It inherits from the FrameBuffer class which provides a pixel buffer which can be drawn upon
        with pixels, lines, rectangles, ellipses, polygons, text and even other FrameBuffers.

        Parameters
        ----------
        spi : int
            number of the SPI bus
        dc : int
            GPIO pin number for the D/C signal
        res : int
            GPIO pin number for the RESET signal
        cs : int
            GPIO pin number for the chip select signal
    
        Returns
        -------
            display object
        """
        self.width = WIDTH
        self.height = HEIGHT
        # frame buffer setup 96x64x16bit
        self.buffer = bytearray(self.height * self.width * 2)
        super().__init__(self.buffer, self.width, self.height, framebuf.RGB565)
        # SPI bus setup
        self.rate = SPI_RATE
        self.spi = spi
        self.dc = dc
        self.res = res
        self.cs = cs
        self.dc.init(dc.OUT, value=0)
        self.res.init(res.OUT, value=0)
        self.cs.init(cs.OUT, value=1)
        # power up the display
        self.init_display()

    def write_cmd(self, cmd):
        self.spi.init(baudrate=self.rate, polarity=0, phase=0)
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, buf):
        self.spi.init(baudrate=self.rate, polarity=0, phase=0)
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(buf)
        self.cs(1)

    def init_display(self):
        # toggle the RESET line
        self.res(1)
        time.sleep_ms(1)
        self.res(0)
        time.sleep_ms(10)
        self.res(1)
        # power-up command sequence
        for cmd in (
            DISPLAY_OFF,
            SET_REMAP, 0x72,                # RGB Color
            SET_DISPLAY_START_LINE, 0x0,    # 
            SET_DISPLAY_OFFSET, 0x0,        #
            NORMAL_DISPLAY,                 # set display to normal mode
            SET_MULTIPLEX_RATIO, 0x3F,      # 1/64 duty
            SET_MASTER_CONFIGURE, 0x8E,     #
            POWER_SAVE_MODE, 0x0B,          # power save mode
            PHASE_PERIOD_ADJUSTMENT, 0x31,  # phase 1 and 2 period adjustment
            DISPLAY_CLOCK_DIV, 0xF0,        # 7:4 = Oscillator Frequency, 3:0 = CLK Div Ratio
            SET_PRECHARGE_SPEED_A, 0x64,    # set second pre-charge speed for color A
            SET_PRECHARGE_SPEED_B, 0x78,    # set second pre-charge speed for color B
            SET_PRECHARGE_SPEED_C, 0x64,    # set second pre-charge speed for color C
            SET_PRECHARGE_VOLTAGE, 0x3A,    #
            SET_V_VOLTAGE, 0x3E,            # set Vcomh voltage
            MASTER_CURRENT_CONTROL, 0x06,   # master current control
            SET_CONTRAST_A, 0x91,           # set contrast for color A
            SET_CONTRAST_B, 0x50,           # set contrast for color B
            SET_CONTRAST_C, 0x7D,           # set contrast for color C
            NORMAL_BRIGHTNESS_DISPLAY_ON    # normal brightness display ON
        ):
            self.write_cmd(cmd)
        # clean all possible junk
        self.fill(0x0)
        self.show()

    def show(self):
        """
        Push the whole buffer to the display.
        """
        self.write_cmd(SET_COLUMN_ADDRESS)
        self.write_cmd(0)
        self.write_cmd(self.width - 1)
        self.write_cmd(SET_ROW_ADDRESS)
        self.write_cmd(0)
        self.write_cmd(self.height - 1)
        self.write_data(self.buffer)