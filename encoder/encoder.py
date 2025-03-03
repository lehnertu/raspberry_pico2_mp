#
#   Rotary Encoder library
#   U.Lehnert 09/2024
# 

from machine import Pin, disable_irq, enable_irq

# when these values have to be changed, the interrupts need to be disabled
value_Enc = 0
state_Enc = 0

# GPIO pins used as inputs with pull-up resistors
pin_A = Pin('D22', Pin.IN, Pin.PULL_UP)
pin_B = Pin('D23', Pin.IN, Pin.PULL_UP)

def pin_A_ISR(pin_desc):
    """
    Interrupt service routine attached to pin_A rising and falling edges
    """
    global state_Enc
    # critical section
    irq_state = disable_irq()
    state_Enc += 1
    enable_irq(irq_state)

# attach the ISR to the pin change
pin_A.irq(handler=pin_A_ISR, trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING)
   
"""
void ISR_pin_A()
{
    cli();
    bool state_A = digitalRead(PIN_A);
    switch (state_Enc)
    {
      case -3:              // A=0 B=1
      {
        if (state_A) state_Enc=0;
        // the encoder has moved one step forward
        PhaseSetpoint += PhaseIncrement;
        if (PhaseSetpoint>360.0) PhaseSetpoint-=360.0;
        break;
      };
      case -2:              // A=0 B=0
      {
        if (state_A) state_Enc=-1;
        break;
      };
      case -1:              // A=1 B=0
      {
        if (!state_A) state_Enc=-2;
        break;
      };
      case 0:               // A=1 B=1
      {
        if (!state_A) state_Enc=1;
        break;
      };
      case 1:               // A=0 B=1
      {
        if (state_A) state_Enc=0;
        break;
      }
      case 2:               // A=0 B=0
      {
        if (state_A) state_Enc=3;
        break;
      }
      case 3:               // A=1 B=0
      {
        if (!state_A) state_Enc=2;
        break;
      }
    };
    sei();
}

void ISR_pin_B()
{
    cli();
    bool state_B = digitalRead(PIN_B);
    switch (state_Enc)
    {
      case -3:              // A=0 B=1
      {
        if (!state_B) state_Enc=-2;
        break;
      };
      case -2:              // A=0 B=0
      {
        if (state_B) state_Enc=-3;
        break;
      };
      case -1:              // A=1 B=0
      {
        if (state_B) state_Enc=0;
        break;
      };
      case 0:               // A=1 B=1
      {
        if (!state_B) state_Enc=-1;
        break;
      };
      case 1:               // A=0 B=1
      {
        if (!state_B) state_Enc=2;
        break;
      }
      case 2:               // A=0 B=0
      {
        if (state_B) state_Enc=1;
        break;
      }
      case 3:               // A=1 B=0
      {
        if (state_B) state_Enc=0;
        // the encoder has moved one step backwards
        PhaseSetpoint -= PhaseIncrement;
        if (PhaseSetpoint<0.0) PhaseSetpoint+=360.0;
        break;
      }
    };
    sei();
}

"""
