//
// Created by motawe on 5/19/26.
//

#include "Motor.h"

Motor::Motor(Encoder* encoder, PWM_expander* pwm, PWM_channel channel_a, PWM_channel channel_b, pid_constants* constants) : _encoder(encoder), _pwm(pwm), _channel_a(channel_a), _channel_b(channel_b), _constants(constants) {}

void Motor::set_pid_constants(pid_constants* constants) {
    _constants = constants;
}

int16_t Motor::update_pid(int16_t setpoint, unsigned long dt) {
    int16_t current = _encoder->get_velocity();
    int16_t error = setpoint - current;

    int16_t pout = _constants->kp* error;

    _integral += error * dt;
    int16_t dout = _constants->kd * ((setpoint - current) - last_error)/dt;
    int16_t iout = _constants->ki * _integral;
    int16_t output = pout + dout + iout;

    if (output > 4096)
        output = 4096;
    else if (output < -4096)
        output = -4096;

    move(output);

    return output;
}

void Motor::move(int16_t speed) {
    if(speed < 0) {
        _pwm->set_channel(_channel_b, abs(speed));
        _pwm->set_channel(_channel_a, 0);
    }
    else {
        _pwm->set_channel(_channel_a, abs(speed));
        _pwm->set_channel(_channel_b, 0);
    }
}

void Motor::stop() {
    _pwm->set_channel(_channel_a, 0);
    _pwm->set_channel(_channel_b, 0);
}