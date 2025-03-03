from machine import Pin, PWM

class Servo:
    """
    This class represents the PWM output for a standard R/C servo or motor driver.
    """

    def __init__(self,
                 pin:Pin,
                 symmetric:bool = True,
                 reverse:bool = False,
                 rate:float = 50,
                 min_pulse_ms:float = 1.0,
                 center_pulse_ms:float = 1.5,
                 max_pulse_ms:float = 2.0) :
        """
        Configure a PWM servo output.

        Args:
            pin (Pin): GPIO pin for the pulse output (active high).

            symmetric (bool, optional): input range definition. Defaults to True.
                Symmetric range accepts (-1.0, 1.0) as input (for typical servos centered at 0.0)
                Asymmetric range accepts [0.0, 1.0) as input (for typical motor speed controllers)

            reverse (bool, optional): reverse reaction to the input. Defaults to False.

            rate (float, optional): pulse repetition rate [Hz]. Defaults to 50 Hz.
                Analog servos run at 50 Hz, modern digital servos accept 100 Hz as well.
                There are high-speed servos capable of even higher frequencies.

            min_pulse_ms (float, optional): shortest output pulse length [ms]. Defaults to 1.0 ms.
            center_pulse_ms (float, optional): center pulse length [ms]. Defaults to 1.5 ms.
            max_pulse_ms (float, optional): longest output pulse length [ms]. Defaults to 2.0 ms.
                The configured input range is mapped and clipped to this range of output pulse lengths.
                Typical R/C servos expect a center of 1.5 ms with a range from 1.0 to 2.0 ms
                for full deflection. This range can be extended for some servos.
                A trim of the center position independent of the endpoints is only supported for symmetric range.
        
        The method may raise a ``ValueError`` if the rate is outside the valid range.
        """
        self.pin = pin
        self.symmetric = symmetric
        self.reverse = reverse
        self.rate = rate
        self.min_pulse_ms = min_pulse_ms
        self.center_pulse_ms = center_pulse_ms
        self.max_pulse_ms = max_pulse_ms
        # compute the setpoint for zero input
        if self.reverse :
            self.center_setpoint = (self.max_pulse_ms-self.center_pulse_ms)/(self.max_pulse_ms-self.min_pulse_ms)
        else:
            self.center_setpoint = (self.center_pulse_ms-self.min_pulse_ms)/(self.max_pulse_ms-self.min_pulse_ms)
        self.pwm = PWM(self.pin, freq=int(self.rate), duty_u16=0)
        # set initial value
        self.set_position(0.0)
    
    def set_position(self, value:float) -> None :
        """
        Set the output of an R/C servo or motor driver for a given "logical" setting.
        This scales the value to the range minimum and maximum pulse length and clips out-of-range values.
        The output can be reversed in direction if the servo is configured that way.

        Args:
            value (float): requested setting
                Depending on the range definitions the input can be in the range
                (-1.0, 1.0) for a symmetric range or [0.0, 1.0) otherwise.
                
        """
        # compute setpoint considering the range definitions
        if self.symmetric :
            if value > 0.0 :
                self.setpoint = (1.0-self.center_setpoint)*value + self.center_setpoint
            else :
                self.setpoint = self.center_setpoint*value + self.center_setpoint
        else :
            self.setpoint = value
        if self.reverse :
            self.setpoint = 1.0-self.setpoint
        # range check for setpoint
        if self.setpoint < 0.0 :
            self.setpoint = 0.0
        if self.setpoint > 1.0 :
            self.setpoint = 1.0
        # convert setpoint to nanoseconds pulse duration
        nanos = 1e6* (self.min_pulse_ms + self.setpoint*(self.max_pulse_ms-self.min_pulse_ms))
        self.pwm.duty_ns(int(nanos))

    def set_trim(self, 
                 center_pulse_ms:float,
                 min_pulse_ms:float = 1.0,
                 max_pulse_ms:float = 2.0) -> None :
        """
        Set center and endpoints for symmetric (-1.0, 1.0) travel range.
        Not supported (ineffective) for asymmetric [0.0, 1.0) range.

        Args:
            center_pulse_ms (float): pulse length [ms] for the servo center position
            min_pulse_ms (float, optional): minimum end-point pulse length [ms]. Defaults to 1.0.
            max_pulse_ms (float, optional): maximum end-point pulse length [ms]. Defaults to 2.0.
        """
        if self.symmetric :
            self.min_pulse_ms = min_pulse_ms
            self.center_pulse_ms = center_pulse_ms
            self.max_pulse_ms = max_pulse_ms
            # compute the setpoint for zero input
            if self.reverse :
                self.center_setpoint = (self.max_pulse_ms-self.center_pulse_ms)/(self.max_pulse_ms-self.min_pulse_ms)
            else:
                self.center_setpoint = (self.center_pulse_ms-self.min_pulse_ms)/(self.max_pulse_ms-self.min_pulse_ms)
