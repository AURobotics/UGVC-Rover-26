//
// Created by motawe on 5/19/26.
//

#ifndef FIRMWARE_MOTOR_H
#define FIRMWARE_MOTOR_H

#include "PWM_expander.h"
#include "Encoder.h"
#include <cmath>

typedef struct {
	double kp,ki,kd;
}pid_constants;

class Motor {
	Encoder* _encoder;
	PWM_expander* _pwm;
	PWM_channel _channel_a, _channel_b;
	pid_constants* _constants;

	public:
		Motor(Encoder* encoder, PWM_expander* pwm, PWM_channel channel_a, PWM_channel channel_b, pid_constants* constants);
		void set_pid_constants(pid_constants* constants);
		int16_t update_pid(int16_t setpoint, unsigned long dt);
		void move(int16_t speed);
		void stop();

		int16_t last_error;
		int16_t _integral;
		int16_t max_speed;
};


#endif //FIRMWARE_MOTOR_H