# EulerBucklingTestBench
Arduino compatible software for a Euler buckling test bench.

This is a software for building an Arduino based test bench for testing Euler buckling in 3D printed parts.

It uses an HX711 board for interfacing with a load cell and an 28BYJ-48 stepper motor for liner movement.

The software communicates over the serial Interface at 57600 baudrate.
The following commands are accepted by the software:
go -> start the motor and start outputting sensor readings
stop -> stop the motor and the output of sensor readings
reverse -> reverse the direction of the motor
