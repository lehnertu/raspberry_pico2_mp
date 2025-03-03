Development of an intertial motion integrator
=============================================

Motion data is read from an ICM-20948 sensor at possibly high rate.

Motion data is logged to a file on a LittleFS on SD card.

Time stamp is recorded from utime.ticks_us().
A 32-bit int value overflows after 4294 s - approximately 1h